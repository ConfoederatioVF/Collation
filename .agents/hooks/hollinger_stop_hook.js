"use strict";

let fs = require("node:fs");
let path = require("node:path");

const HOOKS_DIR = "f:\\Active Projects\\Project 1509 - SVEA\\histmap\\1.data_raw\\landuse_Hollinger\\tests\\.stop_hooks";
const TERMINAL_REASONS = new Set([
  "USER_CANCELED",
  "ERROR",
  "MAX_INVOCATIONS",
  "MAX_FORCED_INVOCATIONS",
  "MAX_TOKEN_BUDGET_EXCEEDED",
  "TERMINAL_CUSTOM_HOOK",
  "TERMINAL_STEP_TYPE",
]);

function readStdin () {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => { data += chunk; });
    process.stdin.on("end", () => resolve(data));
  });
}

async function main () {
  let raw = await readStdin();
  let payload = {};
  try {
    if (raw && raw.trim()) payload = JSON.parse(raw);
  } catch (err) {
    process.stdout.write(JSON.stringify({ decision: "stop" }));
    return;
  }

  let reason = String(payload.terminationReason || "");
  if (TERMINAL_REASONS.has(reason)) {
    process.stdout.write(JSON.stringify({ decision: "stop" }));
    return;
  }

  let conv_id = String(payload.conversationId || "");
  if (!conv_id || !fs.existsSync(HOOKS_DIR)) {
    process.stdout.write(JSON.stringify({ decision: "stop" }));
    return;
  }

  let files = fs.readdirSync(HOOKS_DIR).filter((f) => f.endsWith(".lock.json"));
  for (let i = 0; i < files.length; i++) {
    let lock_path = path.join(HOOKS_DIR, files[i]);
    let lock;
    try {
      lock = JSON.parse(fs.readFileSync(lock_path, "utf8"));
    } catch (err) {
      continue;
    }
    if (!lock || lock.active !== true) continue;

    let indicator = lock.indicator || files[i].replace(/\.lock\.json$/, "");
    let state = lock.state || "WORKING";
    let round = lock.round || 0;

    if (lock.worker_id && lock.worker_id === conv_id) {
      if (state === "AWAITING_AUDIT") {
        process.stdout.write(JSON.stringify({ decision: "stop" }));
        return;
      }
      let findings = Array.isArray(lock.findings) ? lock.findings.slice(0, 5).join("; ") : "";
      process.stdout.write(JSON.stringify({
        decision: "continue",
        reason: `STOP HOOK ACTIVE for indicator '${indicator}' (state=${state}, round=${round}). You MUST resolve all open items/auditor findings, set lock state to AWAITING_AUDIT, and send_message to the auditor (${lock.auditor_id || "auditor"}) before pausing.${findings ? " Open findings: " + findings : ""}`,
      }));
      return;
    }

    if (lock.auditor_id && lock.auditor_id === conv_id) {
      if (state === "AWAITING_AUDIT") {
        process.stdout.write(JSON.stringify({
          decision: "continue",
          reason: `STOP HOOK ACTIVE for indicator '${indicator}' (state=AWAITING_AUDIT, round=${round}). Complete literature checks and visual spot-check renders, then either relay findings (set state=NEEDS_FIX & send_message to worker ${lock.worker_id || "worker"}) or lift the stop hook (set active=false, state=APPROVED) if ZERO mistakes exist.`,
        }));
        return;
      }
      process.stdout.write(JSON.stringify({ decision: "stop" }));
      return;
    }
  }

  process.stdout.write(JSON.stringify({ decision: "stop" }));
}

main().catch(() => {
  process.stdout.write(JSON.stringify({ decision: "stop" }));
});
