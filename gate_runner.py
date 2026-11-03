#!/usr/bin/env python3
"""
O9-RD Deterministic Control Plane CLI (gate_runner.py v1.1)
Zero-dependency reference implementation enforcing:
- Single Source of Truth (copies from ./templates/ if available)
- G3 Incremental SHA-256 Baseline Freeze (--force protection & history chain)
- G3 Detached Approval Binding
- G4 Fail-Closed Integrity & Anti-Stubbing (TODO/FIXME, assert True/1, Path.parts matching)
- G5/G6/G7 Verification (Black-box-first ordering, open blocker bugs, RTM & Release sign-off)
"""
import sys
import os
import json
import shutil
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path("o9_workspace")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATE_FILE = WORKSPACE / "project_state.json"
SPEC_FILE = WORKSPACE / "spec_and_contracts.md"
REVIEW_FILE = WORKSPACE / "review_and_defects.yaml"
RTM_FILE = WORKSPACE / "rtm_acceptance.md"

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".sh", ".kt", ".swift"
}
SKIP_DIRS = {".git", "o9_workspace", "docs", "prompts", "templates", "tests", "__pycache__", "node_modules", ".venv"}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def load_state() -> dict:
    if not STATE_FILE.exists():
        print(f"[BLOCKED] Missing {STATE_FILE}. Run: python gate_runner.py init")
        sys.exit(1)
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def cmd_init():
    WORKSPACE.mkdir(exist_ok=True)
    # Single Source of Truth: copy from ./templates/ if present
    for fname in ["project_state.json", "spec_and_contracts.md", "review_and_defects.yaml", "rtm_acceptance.md"]:
        dst = WORKSPACE / fname
        src = TEMPLATES_DIR / fname
        if not dst.exists():
            if src.exists():
                shutil.copyfile(src, dst)
            else:
                dst.write_text(f"# {fname}\n", encoding="utf-8")
    state = load_state()
    state.setdefault("baseline_history", [])
    state.setdefault("audit_events", []).append({"at": now_iso(), "action": "init_workspace"})
    save_state(state)
    print(f"[OK] Initialized O9-RD workspace in ./{WORKSPACE}/ (synced from single source templates).")

def cmd_freeze(force=False):
    state = load_state()
    if not SPEC_FILE.exists():
        print(f"[BLOCKED] Missing {SPEC_FILE}.")
        sys.exit(1)
    active = state.get("active_baseline") or {}
    if active.get("spec_sha256") and not force:
        print(f"[BLOCKED] Baseline {active.get('baseline_id')} already frozen. Use 'freeze --force' to re-freeze and log audit trail.")
        sys.exit(1)

    digest = sha256_file(SPEC_FILE)
    history = state.setdefault("baseline_history", [])
    if active.get("spec_sha256"):
        history.append(active)

    next_num = len(history) + 1
    new_id = f"BL-{next_num:03d}"
    new_baseline = {
        "baseline_id": new_id,
        "parent_baseline_id": active.get("baseline_id"),
        "spec_sha256": digest,
        "frozen_at": now_iso(),
        "forced": bool(force)
    }
    state["active_baseline"] = new_baseline
    state.setdefault("state", {})["phase"] = "G3"
    state.setdefault("audit_events", []).append({
        "at": now_iso(), "action": "freeze_baseline", "baseline_id": new_id, "sha256": digest, "forced": bool(force)
    })
    save_state(state)
    print(f"[G3 FROZEN] {new_id} -> SHA-256: {digest}")

def cmd_approve(approver="HumanOwner"):
    state = load_state()
    active = state.get("active_baseline") or {}
    digest = active.get("spec_sha256")
    if not digest:
        print("[BLOCKED] Cannot approve: No frozen baseline found. Run 'freeze' first.")
        sys.exit(1)
    if sha256_file(SPEC_FILE) != digest:
        print("[BLOCKED] Spec modified after freeze! Re-freeze before approving.")
        sys.exit(1)
    approvals = state.setdefault("detached_approvals", [])
    apr_id = f"APR-G3-{len(approvals)+1:03d}"
    approvals.append({
        "approval_id": apr_id,
        "gate": "G3",
        "decision": "approved",
        "approver": approver,
        "decided_at": now_iso(),
        "bound_baseline_id": active["baseline_id"],
        "bound_spec_sha256": digest
    })
    state["state"]["phase"] = "G4"
    save_state(state)
    print(f"[G3 APPROVED] Detached signature {apr_id} bound to {active['baseline_id']} ({digest[:12]}...)")

def cmd_check(target_dir=".", require_approval=False, gate_stage="G4"):
    """Fail-closed deterministic check for G3/G4/G5/G6/G7."""
    state = load_state()
    if not SPEC_FILE.exists():
        print(f"[BLOCKED] Missing {SPEC_FILE}.")
        sys.exit(1)

    # 1. Fail-Closed Baseline Check
    active = state.get("active_baseline") or {}
    expected_hash = active.get("spec_sha256")
    if not expected_hash:
        print("[BLOCKED] Fail-Closed: No frozen G3 baseline found in project_state.json! Run 'freeze' first.")
        sys.exit(1)

    actual_hash = sha256_file(SPEC_FILE)
    if actual_hash != expected_hash:
        print(f"[BLOCKER] Baseline Tampering Detected! {SPEC_FILE} hash mismatch.\n  Expected: {expected_hash}\n  Actual:   {actual_hash}")
        sys.exit(1)
    print(f"[OK] Baseline {active.get('baseline_id')} SHA-256 verified ({actual_hash[:12]}...)")

    # 2. Detached Approval Verification (if required or in G4+)
    if require_approval or gate_stage in ("G5", "G6", "G7"):
        approvals = state.get("detached_approvals") or []
        valid_apr = any(a.get("decision") == "approved" and a.get("bound_spec_sha256") == expected_hash for a in approvals)
        if not valid_apr:
            print("[BLOCKED] Missing valid detached G3 approval matching current baseline hash!")
            sys.exit(1)
        print("[OK] Detached G3 approval signature verified.")

    # 3. Anti-Stubbing & Vacuous Assertion Scan (using Path.parts)
    stub_re = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
    vacuous_assert_re = re.compile(r"(^\s*assert\s+(True|1)\s*($|#)|assertTrue\(\s*True\s*\)|expect\(\s*true\s*\)\.toBe\(\s*true\s*\))")
    errors = 0
    scanned_files = 0

    target_path = Path(target_dir).resolve()
    self_path = Path(__file__).resolve()

    for root, _, files in os.walk(target_path):
        root_parts = set(Path(root).relative_to(target_path).parts) if Path(root) != target_path else set()
        if root_parts & SKIP_DIRS:
            continue
        for file in files:
            fpath = Path(root) / file
            if fpath.resolve() == self_path or fpath.suffix.lower() not in CODE_EXTENSIONS:
                continue
            scanned_files += 1
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if stub_re.search(line):
                        print(f"[ANTI-STUB BLOCKER] {fpath}:{i} -> {line.strip()}")
                        errors += 1
                    if vacuous_assert_re.search(line):
                        print(f"[FAKE-ASSERT BLOCKER] {fpath}:{i} -> {line.strip()}")
                        errors += 1

    # 4. Optional G5/G6/G7 Gate Checks
    if gate_stage in ("G5", "G6", "G7") and REVIEW_FILE.exists():
        content = REVIEW_FILE.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'status:\s*["\']?(open|fixing|ready-for-retest)["\']?', content):
            print("[BLOCKER] Unclosed defects found in review_and_defects.yaml!")
            errors += 1
    if gate_stage in ("G6", "G7") and RTM_FILE.exists():
        rtm_text = RTM_FILE.read_text(encoding="utf-8", errors="ignore")
        if "not-run" in rtm_text or "failed" in rtm_text:
            print("[BLOCKER] RTM contains 'not-run' or 'failed' acceptance criteria!")
            errors += 1

    if errors > 0:
        print(f"[FAILED] Gate check blocked with {errors} issue(s) across {scanned_files} scanned file(s).")
        sys.exit(1)
    print(f"[PASSED] All deterministic checks passed ({scanned_files} code file(s) scanned).")

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "help"
    if cmd == "init":
        cmd_init()
    elif cmd == "freeze":
        cmd_freeze(force="--force" in args)
    elif cmd == "approve":
        approver = args[1] if len(args) > 1 and not args[1].startswith("--") else "HumanOwner"
        cmd_approve(approver)
    elif cmd == "check":
        target = next((a for a in args[1:] if not a.startswith("--")), ".")
        req_apr = "--require-approval" in args
        stage = next((a.split("=")[1] for a in args[1:] if a.startswith("--gate=")), "G4")
        cmd_check(target, require_approval=req_apr, gate_stage=stage)
    else:
        print("Usage: python gate_runner.py [init | freeze [--force] | approve [name] | check [dir] [--require-approval] [--gate=G4|G5|G6|G7]]")
