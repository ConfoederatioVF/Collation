import asyncio
import datetime
import glob
import json
import os
import re

BATCH_DIR = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\quipu"
CACHE_PATH = r"f:\Active Projects\Project 1509 - SVEA\tests\toponymy_batches\quipu_approved_cache.json"
MAX_CONCURRENCY = 14
AGENT_TIMEOUT_S = 240
MAX_ROUNDS = 5
DATE_RE = re.compile(r"^-?\d+\.\d+\.\d+$")
FOREIGN_SCRIPT_RE = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")

WORKER_SCHEMA = {
    "type": "object",
    "properties": {
        "settlements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "canonical_name": {"type": "string"},
                    "historical_names": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string"},
                                "name": {"type": "string"},
                                "date_source_note": {"type": "string"},
                            },
                            "required": ["date", "name", "date_source_note"],
                        },
                    },
                },
                "required": ["key", "canonical_name", "historical_names"],
            },
        }
    },
    "required": ["settlements"],
}

AUDITOR_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "status": {"type": "string"},
        "errors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["key", "detail"],
            },
        },
    },
    "required": ["approved", "status", "errors"],
}

TOPONYMY_RULES = """STRICT HISTORICAL TOPONYMY RULES (OPERATION VISCOUNT — ZERO TOLERANCE):
1. Anchor EVERY settlement strictly to its exact `ll` (`[lat, lng]`), `c` (country), `r` (region), and `key`. NEVER conflate homonymous places in another department, province, state, or country.
2. Date format: EVERY `date` MUST match `^-?\\d+\\.\\d+\\.\\d+$` (`YYYY.M.D`, e.g. `-400.1.1`, `1536.2.2`, `1867.5.5`), strictly ascending. Keep `date_source_note` ultra-concise (<= 8 words).
3. NEVER use modern census years (`1985.1.1`..`2024.1.1`) or national independence day (`1825.8.6`) as a fake founding date when an actual historical founding, decree, colonial reducción, mission, or pre-colonial date is known. For small rural villages/hamlets/centros poblados/localidades/archaeological sites with NO separately documented founding decree, anchor to the earliest attested horizon (`ey.1.1`) and note e.g. `"Earliest attested rural/archaeological horizon"`.
4. NEVER back-project a modern/republican/20th-century name onto an earlier colonial or pre-colonial date. Use the actual attested name for each era.
5. NEVER encode mere spelling/orthographic variants (`Tiwanaku`->`Tiahuanaco`, `Paisandú`->`Paysandú`) as consecutive renames, and NEVER repeat identical consecutive names.
6. NEVER invent synthetic ethnic labels or ethnonyms (`"Montevideo Charrúa"`, `"Panche"`, `"Lache"`). For archaeological sites, use the documented site name and `ey.1.1`.
7. NEVER include Cyrillic, Arabic, CJK, or Korean characters (all QUIPU countries use Latin script).
8. Preserve every requested input `key` 1-to-1 (zero omissions, zero extras).
9. Keep `canonical_name` clean (standard modern local spelling, no comma inversions, no corrupt glyphs).
"""


def parse_date_tuple(d):
    parts = str(d or "").split(".")
    if len(parts) != 3:
        return (0, 1, 1)
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return (0, 1, 1)


def programmatic_checks(raw_items, resolved_by_key):
    errs = []
    for orig in raw_items:
        k = orig["key"]
        if k not in resolved_by_key:
            errs.append({"key": k, "detail": "Missing settlement key in worker output."})
            continue
        it = resolved_by_key[k]
        cname = str(it.get("canonical_name") or "").strip()
        if not cname or FOREIGN_SCRIPT_RE.search(cname):
            errs.append({"key": k, "detail": f"Invalid or foreign-script canonical_name: {cname!r}"})
        hnames = it.get("historical_names") or []
        if not isinstance(hnames, list) or len(hnames) == 0:
            errs.append({"key": k, "detail": "historical_names must be a non-empty array."})
            continue
        prev_dt = None
        prev_nm = None
        for hn in hnames:
            dt = str(hn.get("date") or "").strip()
            nm = str(hn.get("name") or "").strip()
            if not DATE_RE.match(dt):
                errs.append({"key": k, "detail": f"Malformed date {dt!r}; expected YYYY.M.D."})
            if not nm or FOREIGN_SCRIPT_RE.search(nm):
                errs.append({"key": k, "detail": f"Invalid or foreign-script historical name {nm!r}."})
            dt_t = parse_date_tuple(dt)
            if prev_dt is not None and dt_t < prev_dt:
                errs.append({"key": k, "detail": f"Non-ascending dates: {prev_dt} -> {dt_t}."})
            if prev_nm is not None and nm.lower() == prev_nm.lower():
                errs.append({"key": k, "detail": f"Consecutive duplicate name: {nm!r}."})
            prev_dt = dt_t
            prev_nm = nm
    return errs


async def call_agent_with_retry(agent_type, role, prompt, model, schema, max_attempts=7):
    last_err = None
    cur_model = model
    for attempt in range(1, max_attempts + 1):
        try:
            res = await asyncio.wait_for(
                agent(
                    prompt=prompt,
                    schema=schema,
                    role=role,
                    type_name=agent_type,
                    model=cur_model,
                ),
                timeout=AGENT_TIMEOUT_S,
            )
            return res
        except Exception as e:
            last_err = e
            msg = str(e) or type(e).__name__
            is_transient = (
                isinstance(e, asyncio.TimeoutError)
                or ("429" in msg)
                or ("RESOURCE_EXHAUSTED" in msg)
                or ("without calling finish" in msg)
                or ("503" in msg)
                or ("500" in msg)
                or ("DEADLINE" in msg)
                or ("UNAVAILABLE" in msg)
                or ("Timeout" in msg)
            )
            if attempt < max_attempts and is_transient:
                wait_s = min(90, 10 * attempt + 5)
                log(f"[retry {attempt}/{max_attempts}] {role} ({msg[:75]}); sleeping {wait_s}s...")
                await asyncio.sleep(wait_s)
                if attempt >= 5 and ("429" in msg or "RESOURCE_EXHAUSTED" in msg):
                    cur_model = "inherit" if cur_model == "flash" else "flash"
            else:
                raise last_err
    raise last_err


# Shared in-memory approved cache
approved_cache = {}
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            approved_cache = json.load(f)
    except Exception:
        approved_cache = {}

cache_lock = asyncio.Lock()
progress_state = {"done_chunks": 0, "approved_chunks": 0, "failed_chunks": []}


def compact_item(s):
    out = {
        "key": s["key"],
        "n": s["name"],
        "c": s.get("country"),
        "r": s.get("region"),
        "ll": s.get("coords_lat_lng"),
        "ey": s.get("earliest_year"),
        "ly": s.get("latest_year"),
        "p": s.get("max_pop"),
    }
    if s.get("is_capital"):
        out["cap"] = True
    ex = s.get("existing_historical_names")
    if ex:
        out["ex"] = ex
    al = [a for a in (s.get("known_aliases") or []) if a and a.lower() != str(s["name"]).lower()][:3]
    if al:
        out["al"] = al
    return out


def materialize_completed_batches(all_batch_files):
    written_approved = 0
    unapproved_batches = []
    total_settlements = 0
    for idx, bp in enumerate(all_batch_files, start=1):
        with open(bp, "r", encoding="utf-8") as f:
            bdata = json.load(f)
        items = bdata.get("settlements") or []
        total_settlements += len(items)
        all_hit = True
        merged = []
        for orig in items:
            c = approved_cache.get(orig["key"])
            if c and c.get("canonical_name") and c.get("historical_names"):
                m = dict(orig)
                m["canonical_name"] = c["canonical_name"]
                m["historical_names"] = c["historical_names"]
                merged.append(m)
            else:
                all_hit = False
                merged.append(dict(orig))
        if all_hit:
            rp = os.path.join(BATCH_DIR, f"resolved_batch_{idx:03d}.json")
            if not os.path.exists(rp):
                out_obj = {
                    "approved_by_auditor": True,
                    "batch_index": idx,
                    "count": len(merged),
                    "project": "QUIPU",
                    "settlements": merged,
                }
                with open(rp, "w", encoding="utf-8") as f:
                    json.dump(out_obj, f, ensure_ascii=False, indent=2)
            written_approved += 1
        else:
            unapproved_batches.append(idx)
    return written_approved, unapproved_batches, total_settlements


async def persist_approved_entries(entries_dict, all_batch_files, total_chunks):
    async with cache_lock:
        approved_cache.update(entries_dict)
        tmp_p = CACHE_PATH + ".tmp"
        with open(tmp_p, "w", encoding="utf-8") as f:
            json.dump(approved_cache, f, ensure_ascii=False)
        os.replace(tmp_p, CACHE_PATH)
        progress_state["done_chunks"] += 1
        progress_state["approved_chunks"] += 1
        if progress_state["done_chunks"] % 15 == 0 or progress_state["done_chunks"] == total_chunks:
            mat_ok, _, _ = materialize_completed_batches(all_batch_files)
            log(
                f"[progress] chunks={progress_state['done_chunks']}/{total_chunks} "
                f"(approved={progress_state['approved_chunks']}) | cache={len(approved_cache)} | "
                f"materialized_batches={mat_ok}/{len(all_batch_files)}"
            )


async def process_and_audit_chunk(chunk_spec, sem, all_batch_files, total_chunks):
    async with sem:
        cid = chunk_spec["chunk_id"]
        tier = chunk_spec["tier"]
        raw_items = chunk_spec["items"]
        raw_by_key = {s["key"]: s for s in raw_items}
        compact_by_key = {s["key"]: compact_item(s) for s in raw_items}

        resolved_by_key = {}
        pending_keys = [s["key"] for s in raw_items]
        last_errors = []
        approved = False

        try:
            for rnd in range(1, MAX_ROUNDS + 1):
                worker_model = "inherit" if rnd >= 3 else "flash"
                auditor_model = "inherit" if rnd >= 3 else "flash"

                req_input = [compact_by_key[k] for k in pending_keys]
                if rnd == 1:
                    w_prompt = (
                        f"Resolve accurate historical toponymy timelines for QUIPU Chunk {cid:03d} ({tier}, {len(req_input)} settlements).\n"
                        f"{TOPONYMY_RULES}\n\n"
                        f"Return JSON matching schema with one entry per `key`.\n\n"
                        f"INPUT:\n{json.dumps(req_input, ensure_ascii=False)}"
                    )
                else:
                    prev_sub = [resolved_by_key[k] for k in pending_keys if k in resolved_by_key]
                    w_prompt = (
                        f"CRITICAL FAILURE REPORTED BY TOPONYMY AUDITOR for QUIPU Chunk {cid:03d} ({len(req_input)} failed settlement(s))!\n"
                        f"Fix EVERY historical/factual/schema error listed below.\n"
                        f"{TOPONYMY_RULES}\n\n"
                        f"CRITICAL AUDITOR ERRORS:\n{json.dumps(last_errors, ensure_ascii=False)}\n\n"
                        f"INPUT METADATA FOR FAILED KEYS:\n{json.dumps(req_input, ensure_ascii=False)}\n\n"
                        f"PREVIOUS DRAFT FOR FAILED KEYS:\n{json.dumps(prev_sub, ensure_ascii=False)}"
                    )

                w_res = await call_agent_with_retry(
                    "self", f"QUIPU Flash C{cid:03d} r{rnd}", w_prompt, worker_model, WORKER_SCHEMA
                )
                for it in (w_res.get("settlements") or []):
                    if isinstance(it, dict) and it.get("key") in raw_by_key:
                        resolved_by_key[it["key"]] = it

                # Programmatic schema check on pending keys
                prog_errs = programmatic_checks([raw_by_key[k] for k in pending_keys], resolved_by_key)
                if prog_errs:
                    bad_ks = sorted(set(e["key"] for e in prog_errs if e["key"] in raw_by_key))
                    pending_keys = bad_ks if bad_ks else pending_keys
                    last_errors = prog_errs
                    log(f"[CRITICAL-SCHEMA] C{cid:03d} r{rnd}: {len(prog_errs)} err on {len(pending_keys)} key(s); patching.")
                    continue

                # Independent read-only auditor verifies ONLY the pending_keys (full chunk on r1, patched keys on r2+)
                aud_input = [compact_by_key[k] for k in pending_keys]
                aud_prop = [resolved_by_key[k] for k in pending_keys]
                aud_prompt = (
                    f"You are the strictly independent read-only TOPONYMY AUDITOR for QUIPU Chunk {cid:03d} ({len(pending_keys)} settlements).\n"
                    f"{TOPONYMY_RULES}\n\n"
                    f"Audit EVERY entry's `canonical_name` and `historical_names` against `ll`, `c`, `r`, `ey`.\n"
                    f"If you find ANY genuine historical mistake (wrong-location conflation, anachronistic back-projection, fake spelling-variant rename, synthetic ethnonym, placeholder census/independence date when an earlier founding/creation date is historically known, missing major documented rename, or schema error), return `approved: false`, `status: 'CRITICAL_FAILURE'`, and list ONLY the offending keys in `errors`.\n"
                    f"Do NOT flag rural villages/hamlets/archaeological sites legitimately anchored to `ey.1.1` when no separate founding decree exists.\n"
                    f"If all {len(pending_keys)} entries are accurate, return `approved: true`, `status: 'APPROVED'`, `errors: []`.\n\n"
                    f"INPUT:\n{json.dumps(aud_input, ensure_ascii=False)}\n\n"
                    f"PROPOSED:\n{json.dumps(aud_prop, ensure_ascii=False)}"
                )
                aud_res = await call_agent_with_retry(
                    "research", f"QUIPU Auditor C{cid:03d} r{rnd}", aud_prompt, auditor_model, AUDITOR_SCHEMA
                )
                aud_errs = aud_res.get("errors") or []
                if aud_res.get("approved") is True and len(aud_errs) == 0:
                    approved = True
                    last_errors = []
                    break
                else:
                    bad_ks = []
                    for e in aud_errs:
                        ek = e.get("key")
                        if ek in raw_by_key and ek not in bad_ks:
                            bad_ks.append(ek)
                    # Lock all clean keys from this round! Only patch the flagged keys!
                    if bad_ks:
                        pending_keys = bad_ks
                    last_errors = aud_errs if aud_errs else [{"key": pending_keys[0], "detail": "CRITICAL FAILURE: Auditor rejected without error details."}]
                    log(f"[CRITICAL FAILURE] C{cid:03d} r{rnd} rejected ({len(last_errors)} err on {len(pending_keys)} key(s)); patching.")

            # Even if a chunk exhausts MAX_ROUNDS on 1-2 stubborn keys, save all already-approved clean keys!
            clean_to_save = {}
            failed_set = set() if approved else set(pending_keys)
            for k, it in resolved_by_key.items():
                if k not in failed_set and not programmatic_checks([raw_by_key[k]], {k: it}):
                    clean_to_save[k] = {
                        "canonical_name": it["canonical_name"],
                        "historical_names": it["historical_names"],
                    }
            if clean_to_save:
                if approved:
                    await persist_approved_entries(clean_to_save, all_batch_files, total_chunks)
                else:
                    async with cache_lock:
                        approved_cache.update(clean_to_save)
                        tmp_p = CACHE_PATH + ".tmp"
                        with open(tmp_p, "w", encoding="utf-8") as f:
                            json.dump(approved_cache, f, ensure_ascii=False)
                        os.replace(tmp_p, CACHE_PATH)
                        progress_state["done_chunks"] += 1
                        progress_state["failed_chunks"].append({"chunk_id": cid, "failed_keys": list(failed_set), "errors": last_errors})
            else:
                async with cache_lock:
                    progress_state["done_chunks"] += 1
                    progress_state["failed_chunks"].append({"chunk_id": cid, "failed_keys": list(failed_set), "errors": last_errors})

            return {"chunk_id": cid, "approved": approved, "saved": len(clean_to_save), "remaining": len(failed_set)}
        except Exception as e:
            log(f"[CHUNK-ERROR] C{cid:03d} fatal after retries: {str(e)[:120]}")
            async with cache_lock:
                progress_state["done_chunks"] += 1
                progress_state["failed_chunks"].append({"chunk_id": cid, "error": str(e)[:200]})
            return {"chunk_id": cid, "approved": False, "saved": 0, "remaining": len(raw_items)}


phase("Discover remaining QUIPU settlements and build tiered chunks")
all_batch_files = sorted(glob.glob(os.path.join(BATCH_DIR, "batch_*.json")))
total_batches = len(all_batch_files)
t_hi, t_mid, t_lo = [], [], []
seen_keys = set()
for bp in all_batch_files:
    with open(bp, "r", encoding="utf-8") as f:
        bdata = json.load(f)
    for s in (bdata.get("settlements") or []):
        k = s["key"]
        if k in approved_cache and approved_cache[k].get("canonical_name") and approved_cache[k].get("historical_names"):
            continue
        if k in seen_keys:
            continue
        seen_keys.add(k)
        mp = s.get("max_pop") or 0
        if mp >= 10000 or s.get("is_capital"):
            t_hi.append(s)
        elif mp >= 2000:
            t_mid.append(s)
        else:
            t_lo.append(s)

chunks = []
cid_counter = 1
for tier_name, arr, sz in [("tier_ge10k", t_hi, 60), ("tier_2k_10k", t_mid, 90), ("tier_lt2k", t_lo, 125)]:
    for i in range(0, len(arr), sz):
        chunks.append({"chunk_id": cid_counter, "tier": tier_name, "items": arr[i : i + sz]})
        cid_counter += 1

log(
    f"Batches={total_batches}, cached_approved={len(approved_cache)}, "
    f"remaining={len(t_hi)+len(t_mid)+len(t_lo)} (ge10k={len(t_hi)}, 2k_10k={len(t_mid)}, lt2k={len(t_lo)}), "
    f"chunks={len(chunks)}, max_concurrency={MAX_CONCURRENCY}"
)

phase(f"Run continuous Flash + Read-Only Auditor swarm ({len(chunks)} chunks, sem={MAX_CONCURRENCY})")
sem = asyncio.Semaphore(MAX_CONCURRENCY)
tasks = [process_and_audit_chunk(c, sem, all_batch_files, len(chunks)) for c in chunks]
chunk_results = await asyncio.gather(*tasks)

phase("Final materialization and auditor_signoff.json")
approved_total, unapproved_list, total_settlements = materialize_completed_batches(all_batch_files)
errors_remaining = len(unapproved_list)
signoff = {
    "approved": (approved_total == total_batches and errors_remaining == 0),
    "auditor_role": "toponymy_auditor",
    "batches_approved": approved_total,
    "batches_total": total_batches,
    "errors_remaining": errors_remaining,
    "failed_chunks_count": len(progress_state["failed_chunks"]),
    "project": "QUIPU",
    "settlements_total": total_settlements,
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "unapproved_batches": unapproved_list[:50],
}
signoff_path = os.path.join(BATCH_DIR, "auditor_signoff.json")
with open(signoff_path, "w", encoding="utf-8") as f:
    json.dump(signoff, f, ensure_ascii=False, indent=2)
log(f"Signoff written: approved={signoff['approved']}, {approved_total}/{total_batches} batches approved, errors_remaining={errors_remaining}")
print(json.dumps(signoff, indent=2))
