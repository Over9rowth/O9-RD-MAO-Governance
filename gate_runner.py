#!/usr/bin/env python3
"""
O9-RD Deterministic Control Plane CLI (gate_runner.py)
Zero-dependency script for initializing workspace, freezing SHA-256 baselines,
and scanning for AI reward-hacking (TODO stubs / baseline tampering).
"""
import sys
import os
import json
import hashlib
import re
from datetime import datetime, timezone

WORKSPACE = "o9_workspace"
STATE_FILE = os.path.join(WORKSPACE, "project_state.json")
SPEC_FILE = os.path.join(WORKSPACE, "spec_and_contracts.md")
REVIEW_FILE = os.path.join(WORKSPACE, "review_and_defects.yaml")
RTM_FILE = os.path.join(WORKSPACE, "rtm_acceptance.md")

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def cmd_init():
    os.makedirs(WORKSPACE, exist_ok=True)
    if not os.path.exists(STATE_FILE):
        state = {
            "project_id": "PRJ-001",
            "sop_version": "O9-RD-Next-V1.0",
            "route": "M",
            "state": {"phase": "G0", "execution_state": "active", "gate_results": {}},
            "active_baseline": {"baseline_id": None, "spec_sha256": None, "frozen_at": None},
            "detached_approvals": []
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    if not os.path.exists(SPEC_FILE):
        with open(SPEC_FILE, "w", encoding="utf-8") as f:
            f.write("# Spec & Three-Tier Contracts (G0.5 & G1)\n\n## 1. G0.5 Two-Way Confirmation\n- **In-Scope**:\n- **Out-of-Scope**:\n- **Acceptance Criteria (AC-001)**:\n\n## 2. G1 Contracts (Schema / Behavior / Test Harness)\n- **Startup & Test Command**:\n")
    if not os.path.exists(REVIEW_FILE):
        with open(REVIEW_FILE, "w", encoding="utf-8") as f:
            f.write("# G2 Blind Reviews & G5 Defects Ledger\ng2_findings: []\ndefects: []\n")
    if not os.path.exists(RTM_FILE):
        with open(RTM_FILE, "w", encoding="utf-8") as f:
            f.write("# G6 Requirements Traceability Matrix (RTM) & G7 Sign-Off\n| AC-ID | Code Ref | Test Run ID | Result |\n|---|---|---|---|\n")
    print(f"[OK] Initialized O9-RD 4-artifact workspace in ./{WORKSPACE}/")

def cmd_freeze():
    if not os.path.exists(SPEC_FILE) or not os.path.exists(STATE_FILE):
        print("[ERROR] Workspace not initialized. Run: python gate_runner.py init")
        sys.exit(1)
    digest = sha256_file(SPEC_FILE)
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    now = datetime.now(timezone.utc).isoformat()
    state["active_baseline"] = {"baseline_id": "BL-001", "spec_sha256": digest, "frozen_at": now}
    state["state"]["phase"] = "G3"
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"[G3 FROZEN] Locked {SPEC_FILE}\n  -> SHA-256: {digest}")

def cmd_check(target_dir="."):
    errors = 0
    if os.path.exists(STATE_FILE) and os.path.exists(SPEC_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        expected = state.get("active_baseline", {}).get("spec_sha256")
        if expected:
            actual = sha256_file(SPEC_FILE)
            if actual != expected:
                print(f"[BLOCKER] Baseline Tampering Detected! {SPEC_FILE} hash mismatch.\n  Expected: {expected}\n  Actual:   {actual}")
                errors += 1
            else:
                print(f"[OK] Baseline SHA-256 verified ({actual[:12]}...)")
    stub_pattern = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
    for root, _, files in os.walk(target_dir):
        if any(skip in root for skip in [".git", WORKSPACE, "docs", "prompts", "templates"]):
            continue
        for file in files:
            if file == "gate_runner.py" or not file.endswith((".py", ".ts", ".js", ".go", ".rs", ".java")):
                continue
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if stub_pattern.search(line):
                        print(f"[ANTI-STUB WARNING] {path}:{i} -> {line.strip()}")
                        errors += 1
    if errors > 0:
        print(f"[FAILED] Gate check blocked with {errors} issue(s).")
        sys.exit(1)
    print("[PASSED] All deterministic control-plane checks passed.")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "init": cmd_init()
    elif cmd == "freeze": cmd_freeze()
    elif cmd == "check": cmd_check(sys.argv[2] if len(sys.argv) > 2 else ".")
    else:
        print("Usage: python gate_runner.py [init | freeze | check <src_dir>]")
