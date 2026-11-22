"""Universal resource-bounded command launcher & single-source pipeline mutex for Operation Viscount.

Reads workstation limits dynamically from `common/defines/geopng_compute.json5` and guarantees:
1. Win32 Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) atomic child/grandchild teardown (0 orphans).
2. `BELOW_NORMAL_PRIORITY_CLASS` CPU scheduling so desktop/IDE/DWM responsiveness never degrades.
3. Mandatory BLAS/OpenMP/libuv/Node heap environment caps (`OMP_NUM_THREADS`, `NODE_OPTIONS`, etc.).
4. Single-source exclusive mutex locking (`histmap/.locks/<name>.lock`) with stale-PID recovery.
5. Working-set RAM & wall-clock timeout watchdog + `--audit-orphans` workspace process check.
"""

import argparse
import ctypes
from ctypes import wintypes
import json
import os
import re
import subprocess
import sys
import time


DEFAULT_LIMITS = {
  "max_workers": 4,
  "max_threads": 8,
  "max_ram_mb": 6144,
  "priority_below_normal": True,
  "enforce_job_object": True,
}

ORPHAN_CANDIDATE_EXES = {
  "chrome.exe",
  "chromedriver.exe",
  "msedgedriver.exe",
  "geckodriver.exe",
  "node.exe",
  "python.exe",
  "rscript.exe",
  "xelatex.exe",
  "pdflatex.exe",
}


def find_svea_root (arg0_start=None):
  """Locates SVEA repository root by walking parent directories."""
  cur = os.path.abspath(arg0_start or os.getcwd())
  if not os.path.isdir(cur):
    cur = os.path.dirname(cur)
  for _ in range(12):
    if os.path.isdir(os.path.join(cur, "histmap")) and os.path.isdir(os.path.join(cur, ".agents")):
      return cur
    parent = os.path.dirname(cur)
    if parent == cur:
      break
    cur = parent

  #Return statement
  return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.."))


def load_compute_limits (arg0_svea_root):
  """Loads CPU/RAM/Job-Object limits from `common/defines/geopng_compute.json5`."""
  limits = dict(DEFAULT_LIMITS)
  cfg_path = os.path.join(arg0_svea_root, "common", "defines", "geopng_compute.json5")
  if not os.path.isfile(cfg_path):
    return limits

  try:
    raw = open(cfg_path, "r", encoding="utf-8", errors="replace").read()
    cleaned = re.sub(r"//.*?$|/\*.*?\*/", "", raw, flags=re.MULTILINE | re.DOTALL)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    cleaned = re.sub(r'([{\s,])([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', cleaned)
    data = json.loads(cleaned)
    cpu_cfg = data.get("cpu") or {}
    native_cfg = data.get("native") or {}
    ram_cfg = data.get("ram") or {}
    limits["max_workers"] = max(1, min(8, int(cpu_cfg.get("max_workers") or limits["max_workers"])))
    limits["max_threads"] = max(1, min(12, int(native_cfg.get("max_threads") or limits["max_threads"])))
    limits["max_ram_mb"] = max(1024, min(8192, int(ram_cfg.get("max_ram_mb") or limits["max_ram_mb"])))
    limits["priority_below_normal"] = bool(cpu_cfg.get("priority_below_normal", True))
    limits["enforce_job_object"] = bool(native_cfg.get("enforce_job_object", True))
  except Exception:
    pass

  #Return statement
  return limits


def is_pid_alive (arg0_pid):
  """Returns True when `arg0_pid` refers to a currently live OS process."""
  pid = int(arg0_pid or 0)
  if pid <= 0:
    return False
  if os.name == "nt":
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
      return False
    try:
      exit_code = wintypes.DWORD()
      if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
        return exit_code.value == STILL_ACTIVE
      return True
    finally:
      kernel32.CloseHandle(handle)

  try:
    os.kill(pid, 0)
    return True
  except OSError:
    return False


def acquire_mutex_lock (arg0_svea_root, arg1_lock_name, arg2_project, arg3_cmd, arg4_wait_seconds=0):
  """Acquires a single canonical atomic lockfile under `histmap/.locks/<name>.lock` with stale-PID recovery."""
  safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(arg1_lock_name or "").strip()).strip("_")
  if not safe_name:
    return None

  locks_dir = os.path.join(arg0_svea_root, "histmap", ".locks")
  os.makedirs(locks_dir, exist_ok=True)
  lock_path = os.path.join(locks_dir, f"{safe_name}.lock")
  deadline = time.monotonic() + max(0.0, float(arg4_wait_seconds or 0.0))

  payload = {
    "command": " ".join(arg3_cmd)[:400],
    "lock_name": safe_name,
    "pid": os.getpid(),
    "project": str(arg2_project or "UNSPECIFIED").upper(),
    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  }

  while True:
    try:
      fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
      try:
        os.write(fd, json.dumps(payload, indent=2).encode("utf-8"))
      finally:
        os.close(fd)
      return lock_path
    except FileExistsError:
      owner = {}
      try:
        owner = json.loads(open(lock_path, "r", encoding="utf-8", errors="replace").read())
      except Exception:
        owner = {}

      owner_pid = int(owner.get("pid") or 0)
      if owner_pid <= 0 or not is_pid_alive(owner_pid):
        try:
          os.remove(lock_path)
          print(f"[run_bounded] Reclaimed stale mutex lock `{safe_name}` from exited PID {owner_pid}.", file=sys.stderr)
          continue
        except OSError:
          pass

      if time.monotonic() >= deadline:
        raise RuntimeError(
          f"[LOCK_CONFLICT] Mutex `{safe_name}` is currently held by active PID {owner_pid} "
          f"(project={owner.get('project', '?')}, started={owner.get('started_utc', '?')}). "
          "Serialize Stadestér/Velkscala/Dataview/GPU stages instead of running concurrently."
        )
      time.sleep(1.5)


def release_mutex_lock (arg0_lock_path):
  """Releases a mutex lockfile if owned by the current process."""
  if not arg0_lock_path or not os.path.isfile(arg0_lock_path):
    return
  try:
    owner = json.loads(open(arg0_lock_path, "r", encoding="utf-8", errors="replace").read())
    if int(owner.get("pid") or 0) == os.getpid():
      os.remove(arg0_lock_path)
  except OSError:
    pass


def create_win32_kill_on_close_job ():
  """Creates a Win32 Job Object configured with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE."""
  if os.name != "nt":
    return None

  JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
  JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

  class IO_COUNTERS (ctypes.Structure):
    _fields_ = [
      ("ReadOperationCount", ctypes.c_uint64),
      ("WriteOperationCount", ctypes.c_uint64),
      ("OtherOperationCount", ctypes.c_uint64),
      ("ReadTransferCount", ctypes.c_uint64),
      ("WriteTransferCount", ctypes.c_uint64),
      ("OtherTransferCount", ctypes.c_uint64),
    ]

  class JOBOBJECT_BASIC_LIMIT_INFORMATION (ctypes.Structure):
    _fields_ = [
      ("PerProcessUserTimeLimit", ctypes.c_int64),
      ("PerJobUserTimeLimit", ctypes.c_int64),
      ("LimitFlags", wintypes.DWORD),
      ("MinimumWorkingSetSize", ctypes.c_size_t),
      ("MaximumWorkingSetSize", ctypes.c_size_t),
      ("ActiveProcessLimit", wintypes.DWORD),
      ("Affinity", ctypes.c_size_t),
      ("PriorityClass", wintypes.DWORD),
      ("SchedulingClass", wintypes.DWORD),
    ]

  class JOBOBJECT_EXTENDED_LIMIT_INFORMATION (ctypes.Structure):
    _fields_ = [
      ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
      ("IoInfo", IO_COUNTERS),
      ("ProcessMemoryLimit", ctypes.c_size_t),
      ("JobMemoryLimit", ctypes.c_size_t),
      ("PeakProcessMemoryUsed", ctypes.c_size_t),
      ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

  kernel32 = ctypes.windll.kernel32
  kernel32.CreateJobObjectW.restype = wintypes.HANDLE
  job = kernel32.CreateJobObjectW(None, None)
  if not job:
    return None

  info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
  info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
  ok = kernel32.SetInformationJobObject(
    job,
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
    ctypes.byref(info),
    ctypes.sizeof(info),
  )
  if not ok:
    kernel32.CloseHandle(job)
    return None

  #Return statement
  return job


def assign_process_to_job (arg0_job, arg1_proc_handle):
  """Assigns a child process handle into an active Win32 Job Object."""
  if os.name != "nt" or not arg0_job or not arg1_proc_handle:
    return False
  kernel32 = ctypes.windll.kernel32
  return bool(kernel32.AssignProcessToJobObject(arg0_job, wintypes.HANDLE(int(arg1_proc_handle))))


def get_process_rss_mb (arg0_pid):
  """Returns current resident working-set memory in MiB for `arg0_pid`, or 0.0 if unavailable."""
  if os.name != "nt":
    return 0.0

  PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
  PROCESS_VM_READ = 0x0010

  class PROCESS_MEMORY_COUNTERS (ctypes.Structure):
    _fields_ = [
      ("cb", wintypes.DWORD),
      ("PageFaultCount", wintypes.DWORD),
      ("PeakWorkingSetSize", ctypes.c_size_t),
      ("WorkingSetSize", ctypes.c_size_t),
      ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
      ("QuotaPagedPoolUsage", ctypes.c_size_t),
      ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
      ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
      ("PagefileUsage", ctypes.c_size_t),
      ("PeakPagefileUsage", ctypes.c_size_t),
    ]

  kernel32 = ctypes.windll.kernel32
  psapi = ctypes.windll.psapi
  handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, int(arg0_pid))
  if not handle:
    return 0.0
  try:
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(pmc)
    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
      return float(pmc.WorkingSetSize) / (1024.0 * 1024.0)
    return 0.0
  finally:
    kernel32.CloseHandle(handle)


def build_bounded_env (arg0_limits, arg1_max_ram_mb, arg2_max_threads, arg3_lock_name):
  """Builds child environment enforcing BLAS, OpenMP, libuv, Python and Node memory caps."""
  env = dict(os.environ)
  threads_str = str(max(1, int(arg2_max_threads)))
  ram_mb = max(1024, min(8192, int(arg1_max_ram_mb)))

  env["OMP_NUM_THREADS"] = threads_str
  env["OPENBLAS_NUM_THREADS"] = threads_str
  env["MKL_NUM_THREADS"] = threads_str
  env["NUMEXPR_MAX_THREADS"] = threads_str
  env["VECLIB_MAXIMUM_THREADS"] = threads_str
  env["BLIS_NUM_THREADS"] = threads_str
  env["UV_THREADPOOL_SIZE"] = threads_str
  env["VISCOUNT_MAX_WORKERS"] = str(arg0_limits["max_workers"])
  env["VISCOUNT_MAX_RAM_MB"] = str(ram_mb)
  if arg3_lock_name:
    env["VISCOUNT_ACTIVE_LOCK"] = str(arg3_lock_name)

  existing_node_opts = env.get("NODE_OPTIONS", "").strip()
  if "--max-old-space-size=" in existing_node_opts:
    existing_node_opts = re.sub(r"--max-old-space-size=\d+", f"--max-old-space-size={ram_mb}", existing_node_opts)
  else:
    existing_node_opts = f"{existing_node_opts} --max-old-space-size={ram_mb}".strip()
  env["NODE_OPTIONS"] = existing_node_opts

  #Return statement
  return env


def audit_workspace_orphans (arg0_svea_root):
  """Inspects live OS processes whose command line references this workspace and flags potential orphans."""
  findings = []
  if os.name != "nt":
    return findings

  ps_cmd = (
    "Get-CimInstance Win32_Process | "
    "Select-Object ProcessId, ParentProcessId, Name, CommandLine, WorkingSetSize | "
    "ConvertTo-Json -Compress"
  )
  res = subprocess.run(
    ["powershell", "-NoProfile", "-Command", ps_cmd],
    capture_output=True,
    text=True,
    timeout=20,
  )
  if res.returncode != 0 or not res.stdout.strip():
    return findings

  try:
    rows = json.loads(res.stdout)
  except json.JSONDecodeError:
    return findings
  if isinstance(rows, dict):
    rows = [rows]

  ws_norm = os.path.abspath(arg0_svea_root).replace("\\", "/").lower()
  ws_name = os.path.basename(ws_norm)
  live_pids = {int(r.get("ProcessId") or 0) for r in rows if isinstance(r, dict)}
  my_pid = os.getpid()
  parent_pid = os.getppid()

  for row in rows:
    if not isinstance(row, dict):
      continue
    pid = int(row.get("ProcessId") or 0)
    ppid = int(row.get("ParentProcessId") or 0)
    name = str(row.get("Name") or "").lower()
    cmdline = str(row.get("CommandLine") or "")
    cmd_norm = cmdline.replace("\\", "/").lower()
    if pid in {my_pid, parent_pid} or name not in ORPHAN_CANDIDATE_EXES:
      continue
    is_workspace_proc = (ws_norm in cmd_norm) or (ws_name in cmd_norm) or (
      name in {"chrome.exe", "chromedriver.exe"} and "--headless" in cmd_norm and ("puppeteer" in cmd_norm or "selenium" in cmd_norm or "remote-debugging-port" in cmd_norm)
    )
    if not is_workspace_proc:
      continue
    if ppid not in live_pids or name in {"chromedriver.exe", "xelatex.exe"}:
      rss_mb = round(float(row.get("WorkingSetSize") or 0) / (1024.0 * 1024.0), 1)
      findings.append({
        "cmdline": cmdline[:180],
        "name": name,
        "parent_alive": ppid in live_pids,
        "pid": pid,
        "ppid": ppid,
        "rss_mb": rss_mb,
      })

  #Return statement
  return findings


def main ():
  parser = argparse.ArgumentParser(
    description="Run a command inside a Win32 Job Object at BelowNormal priority with geopng_compute.json5 caps and optional mutex lock."
  )
  parser.add_argument("--lock", default=None, help="Exclusive mutex name under histmap/.locks/<name>.lock (e.g. stadester_velkscala, gpu_compute, dataview_metadata)")
  parser.add_argument("--wait-seconds", type=int, default=0, help="Seconds to wait for mutex lock before failing (default 0 = fail-fast)")
  parser.add_argument("--project", default="UNSPECIFIED", help="Viscount project key for lock diagnostics")
  parser.add_argument("--timeout", type=int, default=0, help="Hard wall-clock timeout in seconds (0 = unlimited)")
  parser.add_argument("--max-ram-mb", type=int, default=0, help="Override working-set RAM cap in MiB (clamped <= 8192)")
  parser.add_argument("--max-threads", type=int, default=0, help="Override BLAS/OpenMP/libuv thread cap (clamped <= 8)")
  parser.add_argument("--cwd", default=None, help="Working directory for child command")
  parser.add_argument("--audit-orphans", action="store_true", help="Inspect and report any orphaned workspace background processes")
  parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute after `--`")
  parsed = parser.parse_args()

  svea_root = find_svea_root(parsed.cwd or os.getcwd())
  if parsed.audit_orphans:
    orphans = audit_workspace_orphans(svea_root)
    if orphans:
      for item in orphans:
        print(
          f"[FAIL] Orphaned/stale process PID={item['pid']} ({item['name']}, {item['rss_mb']} MiB, parent_alive={item['parent_alive']}): {item['cmdline']}",
          file=sys.stderr,
        )
      sys.exit(1)
    print("[run_bounded] PASS: 0 orphaned workspace background processes detected.")
    sys.exit(0)

  cmd_args = list(parsed.cmd or [])
  if cmd_args and cmd_args[0] == "--":
    cmd_args = cmd_args[1:]
  if not cmd_args:
    print("[FAIL] No command provided to run_bounded.py (pass `-- <command> <args>`).", file=sys.stderr)
    sys.exit(2)

  limits = load_compute_limits(svea_root)
  eff_ram = parsed.max_ram_mb if parsed.max_ram_mb > 0 else limits["max_ram_mb"]
  eff_ram = max(1024, min(8192, eff_ram))
  eff_threads = parsed.max_threads if parsed.max_threads > 0 else limits["max_workers"]
  eff_threads = max(1, min(8, eff_threads))

  lock_path = None
  job_handle = None
  proc = None

  try:
    if parsed.lock:
      lock_path = acquire_mutex_lock(svea_root, parsed.lock, parsed.project, cmd_args, parsed.wait_seconds)

    env = build_bounded_env(limits, eff_ram, eff_threads, parsed.lock)
    creation_flags = 0
    if os.name == "nt" and limits["priority_below_normal"]:
      creation_flags |= 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS

    if os.name == "nt" and limits["enforce_job_object"]:
      job_handle = create_win32_kill_on_close_job()

    start_t = time.monotonic()
    proc = subprocess.Popen(
      cmd_args,
      cwd=parsed.cwd or os.getcwd(),
      env=env,
      creationflags=creation_flags,
    )
    if job_handle is not None and hasattr(proc, "_handle"):
      assign_process_to_job(job_handle, proc._handle)

    while True:
      rc = proc.poll()
      if rc is not None:
        sys.exit(rc)

      if parsed.timeout > 0 and (time.monotonic() - start_t) > parsed.timeout:
        print(f"[FAIL] [run_bounded] Timeout exceeded ({parsed.timeout}s); terminating job tree.", file=sys.stderr)
        proc.terminate()
        sys.exit(124)

      rss_mb = get_process_rss_mb(proc.pid)
      if rss_mb > (eff_ram * 1.15):
        print(
          f"[FAIL] [run_bounded] Child PID {proc.pid} exceeded RAM cap ({rss_mb:.1f} MiB > {eff_ram * 1.15:.0f} MiB); terminating job tree.",
          file=sys.stderr,
        )
        proc.terminate()
        sys.exit(137)

      time.sleep(0.5)
  except RuntimeError as exc:
    print(f"[FAIL] {exc}", file=sys.stderr)
    sys.exit(1)
  except KeyboardInterrupt:
    if proc is not None and proc.poll() is None:
      proc.terminate()
    sys.exit(130)
  finally:
    if proc is not None and proc.poll() is None:
      try:
        proc.terminate()
        proc.wait(timeout=3)
      except Exception:
        try:
          proc.kill()
        except Exception:
          pass
    if job_handle is not None and os.name == "nt":
      ctypes.windll.kernel32.CloseHandle(job_handle)
    release_mutex_lock(lock_path)


if __name__ == "__main__":
  main()
