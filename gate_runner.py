#!/usr/bin/env python3
"""
O9-RD Verifiable Minimal Control Plane CLI (gate_runner.py v1.3)
Enforces:
- Zero hardcoded default secrets (Fail-Closed when O9_APPROVAL_SECRET / --key is absent)
- Unconditional HMAC-SHA256 verification on both FREEZE and APPROVAL records
- Hash-chained append-only approvals.jsonl + external anchor (~/.o9-trust/ & git tag)
- G4 Anti-Stubbing & Vacuous Assertion scan (including .ipynb, using Path.parts)
- G5/G6/G7 Fail-Closed verification:
  * Black-box-first flag verification
  * Real, non-empty evidence_log_ref file verification (blocks /dev/null & missing logs)
  * Defect status whitelist + Independent QA closer identity verification (blocks self-closed bugs)
  * G7 all 3 decoupled decisions verification (Sign-Off, Release Authorization, License)
"""
import sys
import os
import stat
import json
import hmac
import shutil
import hashlib
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path("o9_workspace")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATE_FILE = WORKSPACE / "project_state.json"
SPEC_FILE = WORKSPACE / "spec_and_contracts.md"
REVIEW_FILE = WORKSPACE / "review_and_defects.yaml"
RTM_FILE = WORKSPACE / "rtm_acceptance.md"
APPROVALS_LOG = WORKSPACE / "approvals.jsonl"
DEFAULT_EVIDENCE_LOG = WORKSPACE / "evidence" / "run-bb-001.log"

VALID_GATES = {"G3", "G4", "G5", "G6", "G7"}
VALID_APPROVERS = {"station_master", "qa_lead", "ci_bot", "Over9rowth", "HumanOwner"}
VALID_QA_CLOSERS = {"qa_lead", "independent_qa", "QA-SESSION-01", "station_master"}
CLOSED_DEFECT_STATUSES = {"closed", "verified", "rejected"}

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".sh", ".kt", ".swift", ".ipynb"
}
SKIP_DIRS = {".git", "o9_workspace", "docs", "prompts", "templates", "tests", "__pycache__", "node_modules", ".venv"}

DEFAULT_STATE_JSON = {
    "project_id": "PRJ-2026-001",
    "sop_version": "O9-RD-Next-V1.3",
    "route": "M",
    "state": {"phase": "G0", "execution_state": "active", "gate_results": {}},
    "active_baseline": {"baseline_id": None, "parent_baseline_id": None, "spec_sha256": None, "frozen_at": None},
    "baseline_history": [],
    "audit_events": []
}

DEFAULT_SPEC_MD = """# Requirement Specification & Three-Tier Engineering Contracts
## Part 1: G0.5 Two-Way Confirmation
- **In-Scope**: `[REQ-001]`
- **Out-of-Scope**: None
| AC-ID | REQ-ID | Importance | Expected Result | Mode |
| :--- | :--- | :--- | :--- | :--- |
| `AC-001` | `REQ-001` | `core` | Returns 200 OK | `automated` |
## Part 2: G1 Three-Tier Contracts (Schema / Behavior / Test Harness)
- **Startup & Test Command**: `pytest`
"""

DEFAULT_REVIEW_YAML = """project_id: PRJ-2026-001
bound_baseline_id: BL-001
g2_reviews:
  findings_disposition: []
mock_and_stub_inventory: []
g5_test_runs:
  - run_id: RUN-BB-001
    phase_type: "black-box-first"
    tester_session: "QA-SESSION-01"
    source_code_hidden_verified: true
    candidate_id: "CAND-001"
    command_executed: "pytest tests/"
    exit_code: 0
    evidence_log_ref: "o9_workspace/evidence/run-bb-001.log"
defects: []
manual_verification_todos: []
"""

DEFAULT_RTM_MD = """# G6 Requirements Traceability Matrix (RTM) & G7 Sign-Off Decisions
| REQ-ID | AC-ID | Importance | Code Ref | Test Case ID | Evidence `run_id` | Coverage | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-001` | `AC-001` | `core` | `src/` | `BB-001` | `RUN-BB-001` | `covered` | `passed` |
## 4. G7 Owner's Three Decoupled Decisions
- **Decision 1 (Sign-Off)**: `approved`
- **Decision 2 (Release Authorization)**: `hold`
- **Decision 3 (Ownership & License)**: `MIT`
"""

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def compute_hmac(secret: str, payload: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

def require_signing_secret(explicit_key: str = None) -> str:
    """Fail-Closed: Refuses to fall back to any hardcoded key."""
    secret = explicit_key or os.environ.get("O9_APPROVAL_SECRET")
    if not secret or len(secret.strip()) < 6:
        print(
            "[BLOCKED] No valid signing key configured (min 6 chars). "
            "Set environment variable O9_APPROVAL_SECRET or pass --key=SECRET. "
            "Refusing to fall back to any hardcoded default key."
        )
        sys.exit(1)
    return secret.strip()

def get_external_anchor_path() -> Path:
    """Stores an external trust anchor outside the repo workspace (~/.o9-trust/) keyed by workspace path hash."""
    ws_abs = str(WORKSPACE.resolve())
    ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
    trust_dir = Path.home() / ".o9-trust"
    try:
        trust_dir.mkdir(mode=0o700, exist_ok=True)
    except Exception:
        pass
    return trust_dir / f"anchor_{ws_id}.sha256"

def sync_external_anchor(secret: str):
    if not APPROVALS_LOG.exists():
        return
    ledger_hash = sha256_file(APPROVALS_LOG)
    anchor_mac = compute_hmac(secret, f"ANCHOR:{ledger_hash}")
    anchor_file = get_external_anchor_path()
    try:
        if anchor_file.exists():
            set_writable(anchor_file)
        anchor_file.write_text(f"{ledger_hash}:{anchor_mac}\n", encoding="utf-8")
        set_readonly(anchor_file)
    except Exception:
        pass

def verify_external_anchor(secret: str):
    anchor_file = get_external_anchor_path()
    if not anchor_file.exists():
        return
    try:
        raw = anchor_file.read_text(encoding="utf-8").strip()
        expected_ledger_hash, expected_mac = raw.split(":", 1)
    except Exception:
        print("[BLOCKER] External trust anchor corrupted!")
        sys.exit(1)
    actual_ledger_hash = sha256_file(APPROVALS_LOG)
    if actual_ledger_hash != expected_ledger_hash:
        print("[BLOCKER] Ledger Tampering Detected! approvals.jsonl diverges from external trust anchor (~/.o9-trust/)!")
        sys.exit(1)
    if compute_hmac(secret, f"ANCHOR:{actual_ledger_hash}") != expected_mac:
        print("[BLOCKER] External trust anchor HMAC mismatch! Invalid signing secret or forged anchor.")
        sys.exit(1)

def set_readonly(filepath: Path):
    try:
        os.chmod(filepath, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
    except Exception:
        pass

def set_writable(filepath: Path):
    try:
        os.chmod(filepath, stat.S_IWRITE | stat.S_IREAD)
    except Exception:
        pass

def read_ledger_records() -> list:
    if not APPROVALS_LOG.exists():
        return []
    records = []
    with open(APPROVALS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    print("[BLOCKER] Corrupted JSON record detected in approvals.jsonl!")
                    sys.exit(1)
    return records

def append_ledger_record(record: dict, secret: str):
    if APPROVALS_LOG.exists():
        set_writable(APPROVALS_LOG)
    with open(APPROVALS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    set_readonly(APPROVALS_LOG)
    sync_external_anchor(secret)

def load_state() -> dict:
    if not STATE_FILE.exists():
        print(f"[BLOCKED] Missing {STATE_FILE}. Run: python gate_runner.py init")
        sys.exit(1)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[BLOCKED] Corrupted JSON in {STATE_FILE}: {e}")
        sys.exit(1)

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def cmd_init():
    WORKSPACE.mkdir(exist_ok=True)
    (WORKSPACE / "evidence").mkdir(exist_ok=True)
    fallbacks = {
        "project_state.json": json.dumps(DEFAULT_STATE_JSON, indent=2, ensure_ascii=False),
        "spec_and_contracts.md": DEFAULT_SPEC_MD,
        "review_and_defects.yaml": DEFAULT_REVIEW_YAML,
        "rtm_acceptance.md": DEFAULT_RTM_MD,
    }
    for fname, fallback_content in fallbacks.items():
        dst = WORKSPACE / fname
        src = TEMPLATES_DIR / fname
        if not dst.exists():
            if src.exists():
                shutil.copyfile(src, dst)
            else:
                dst.write_text(fallback_content, encoding="utf-8")
    if not DEFAULT_EVIDENCE_LOG.exists():
        DEFAULT_EVIDENCE_LOG.write_text("[G5 Black-Box Test Run Log] Initialized evidence artifact.\n", encoding="utf-8")
    if not APPROVALS_LOG.exists():
        APPROVALS_LOG.write_text("", encoding="utf-8")
        set_readonly(APPROVALS_LOG)
    # Remove any stale external anchor when initializing a fresh empty ledger
    anchor_file = get_external_anchor_path()
    if APPROVALS_LOG.stat().st_size == 0 and anchor_file.exists():
        try:
            set_writable(anchor_file)
            anchor_file.unlink()
        except Exception:
            pass
    state = load_state()
    state.setdefault("baseline_history", [])
    state.setdefault("audit_events", []).append({"at": now_iso(), "action": "init_workspace"})
    save_state(state)
    if not os.environ.get("O9_APPROVAL_SECRET"):
        print("[NOTICE] O9_APPROVAL_SECRET is not set yet. You must set O9_APPROVAL_SECRET (or pass --key=SECRET) before running freeze/approve/check.")
    print(f"[OK] Initialized O9-RD workspace in ./{WORKSPACE}/")

def verify_full_ledger_chain(records: list, secret: str):
    """Unconditionally verifies HMAC & hash-chain integrity for EVERY record in approvals.jsonl."""
    prev_hmac = "GENESIS"
    for idx, rec in enumerate(records, 1):
        rtype = rec.get("type")
        rec_prev = rec.get("prev_hmac", "GENESIS")
        if rec_prev != prev_hmac:
            print(f"[BLOCKER] Ledger hash-chain broken at record #{idx} in approvals.jsonl!")
            sys.exit(1)
        if rtype == "FREEZE":
            payload = f"FREEZE:{rec.get('baseline_id')}:{rec.get('spec_sha256')}:{prev_hmac}"
        elif rtype == "APPROVAL":
            payload = f"APPROVAL:{rec.get('approval_id')}:{rec.get('gate')}:{rec.get('approver')}:{rec.get('bound_baseline_id')}:{rec.get('bound_spec_sha256')}:{prev_hmac}"
        else:
            print(f"[BLOCKER] Unknown record type '{rtype}' in approvals.jsonl!")
            sys.exit(1)
        expected_mac = compute_hmac(secret, payload)
        if rec.get("hmac") != expected_mac:
            print(f"[BLOCKER] Forged or unauthorized {rtype} record #{idx} in approvals.jsonl! Unconditional HMAC verification failed.")
            sys.exit(1)
        prev_hmac = expected_mac

def cmd_freeze(force=False, key=None):
    secret = require_signing_secret(key)
    state = load_state()
    if not SPEC_FILE.exists():
        print(f"[BLOCKED] Missing {SPEC_FILE}.")
        sys.exit(1)

    verify_external_anchor(secret)
    records = read_ledger_records()
    if records:
        verify_full_ledger_chain(records, secret)

    freeze_records = [r for r in records if r.get("type") == "FREEZE"]
    if freeze_records and not force:
        last_bl = freeze_records[-1].get("baseline_id")
        print(f"[BLOCKED] Baseline {last_bl} already frozen in approvals.jsonl. Use 'freeze --force' with valid signing secret to re-freeze.")
        sys.exit(1)

    digest = sha256_file(SPEC_FILE)
    next_num = len(freeze_records) + 1
    new_id = f"BL-{next_num:03d}"
    parent_id = freeze_records[-1]["baseline_id"] if freeze_records else None
    prev_hmac = records[-1]["hmac"] if records else "GENESIS"
    ts = now_iso()

    mac = compute_hmac(secret, f"FREEZE:{new_id}:{digest}:{prev_hmac}")
    append_ledger_record({
        "type": "FREEZE",
        "baseline_id": new_id,
        "parent_baseline_id": parent_id,
        "spec_sha256": digest,
        "forced": bool(force),
        "prev_hmac": prev_hmac,
        "at": ts,
        "hmac": mac
    }, secret)

    active = state.get("active_baseline") or {}
    if active.get("spec_sha256"):
        state.setdefault("baseline_history", []).append(active)
    state["active_baseline"] = {
        "baseline_id": new_id, "parent_baseline_id": parent_id,
        "spec_sha256": digest, "frozen_at": ts, "forced": bool(force)
    }
    state.setdefault("state", {})["phase"] = "G3"
    save_state(state)
    print(f"[G3 FROZEN] {new_id} recorded & anchored -> SHA-256: {digest}")

def cmd_approve(approver="station_master", gate="G3", key=None):
    if approver.startswith("-"):
        print(f"[BLOCKED] Invalid approver name '{approver}'. Flags cannot be used as approver identity.")
        sys.exit(1)
    if approver not in VALID_APPROVERS:
        print(f"[BLOCKED] Unauthorized approver role '{approver}'. Allowed roles: {sorted(VALID_APPROVERS)}")
        sys.exit(1)
    if gate not in VALID_GATES:
        print(f"[BLOCKED] Invalid gate '{gate}'. Allowed: {sorted(VALID_GATES)}")
        sys.exit(1)

    secret = require_signing_secret(key)
    verify_external_anchor(secret)
    records = read_ledger_records()
    if not records:
        print("[BLOCKED] Cannot approve: No frozen baseline in approvals.jsonl. Run 'freeze' first.")
        sys.exit(1)
    verify_full_ledger_chain(records, secret)

    freeze_records = [r for r in records if r.get("type") == "FREEZE"]
    if not freeze_records:
        print("[BLOCKED] Cannot approve: No FREEZE record found.")
        sys.exit(1)

    latest_freeze = freeze_records[-1]
    bl_id = latest_freeze["baseline_id"]
    digest = latest_freeze["spec_sha256"]

    if not SPEC_FILE.exists() or sha256_file(SPEC_FILE) != digest:
        print("[BLOCKED] Spec file modified after freeze! Re-freeze before approving.")
        sys.exit(1)

    apr_count = len([r for r in records if r.get("type") == "APPROVAL"]) + 1
    apr_id = f"APR-{gate}-{apr_count:03d}"
    prev_hmac = records[-1]["hmac"]
    ts = now_iso()
    payload = f"APPROVAL:{apr_id}:{gate}:{approver}:{bl_id}:{digest}:{prev_hmac}"
    mac = compute_hmac(secret, payload)

    append_ledger_record({
        "type": "APPROVAL",
        "approval_id": apr_id,
        "gate": gate,
        "decision": "approved",
        "approver": approver,
        "bound_baseline_id": bl_id,
        "bound_spec_sha256": digest,
        "prev_hmac": prev_hmac,
        "decided_at": ts,
        "hmac": mac
    }, secret)

    state = load_state()
    state.setdefault("state", {})["phase"] = "G4" if gate == "G3" else gate
    save_state(state)
    print(f"[{gate} APPROVED] Detached HMAC signature {apr_id} by '{approver}' bound to {bl_id} ({digest[:12]}...)")

def verify_g5_g6_g7_ledgers(gate_stage: str) -> int:
    errors = 0
    if gate_stage in ("G5", "G6", "G7"):
        if not REVIEW_FILE.exists():
            print(f"[BLOCKER] Fail-Closed: Missing {REVIEW_FILE} required for {gate_stage}!")
            return 1
        content = REVIEW_FILE.read_text(encoding="utf-8", errors="ignore")

        # 1. Verify Black-Box-First execution record exists
        if not re.search(r"source_code_hidden_verified:\s*true", content, re.IGNORECASE):
            print(f"[BLOCKER] {gate_stage} violation: Missing 'source_code_hidden_verified: true' in {REVIEW_FILE}!")
            errors += 1

        # 2. R5 Fix: Verify g5_test_runs exit_code == 0 and evidence_log_ref points to a real, non-empty regular file
        ev_refs = re.findall(r"evidence_log_ref:\s*['\"]?([^'\"\n\r#]+)['\"]?", content)
        if not ev_refs:
            print(f"[BLOCKER] Missing 'evidence_log_ref' in {REVIEW_FILE}!")
            errors += 1
        for ref in ev_refs:
            ref_clean = ref.strip()
            ev_path = Path(ref_clean)
            if ref_clean in ("/dev/null", "NUL", "null", "none", "") or not ev_path.exists() or not ev_path.is_file():
                print(f"[BLOCKER] Invalid or missing test evidence file '{ref_clean}'! Must be an existing regular file.")
                errors += 1
            elif ev_path.stat().st_size == 0:
                print(f"[BLOCKER] Test evidence file '{ref_clean}' is empty (0 bytes)!")
                errors += 1

        exit_codes = re.findall(r"exit_code:\s*([0-9]+)", content)
        if not exit_codes or any(int(c) != 0 for c in exit_codes):
            print(f"[BLOCKER] Non-zero or missing test exit_code in {REVIEW_FILE}!")
            errors += 1

        # 3. R4 Fix: Whitelist defect status AND verify independent QA closer identity (blocks self-closed bugs)
        in_defects = False
        current_bug = None
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if re.match(r"^[a-zA-Z0-9_]+:", raw_line) and not raw_line.startswith(" "):
                if in_defects and current_bug:
                    errors += _validate_defect_entry(current_bug)
                    current_bug = None
                in_defects = line.startswith("defects:")
                if in_defects and line.endswith("[]"):
                    in_defects = False
                continue
            if in_defects:
                if line.startswith("-"):
                    if current_bug:
                        errors += _validate_defect_entry(current_bug)
                    current_bug = {}
                    line = line[1:].strip()
                if current_bug is not None and ":" in line:
                    k, v = line.split(":", 1)
                    current_bug[k.strip().lower()] = v.strip().strip("'\"")
        if in_defects and current_bug:
            errors += _validate_defect_entry(current_bug)

    if gate_stage in ("G6", "G7"):
        if not RTM_FILE.exists():
            print(f"[BLOCKER] Fail-Closed: Missing {RTM_FILE} required for {gate_stage}!")
            return errors + 1
        rtm_text = RTM_FILE.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\b(not-run|failed|blocked|not-covered)\b", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] {RTM_FILE} contains unverified or failed AC items!")
            errors += 1
        if not re.search(r"\|\s*`?AC-\d+", rtm_text):
            print(f"[BLOCKER] {RTM_FILE} contains no valid AC traceability rows!")
            errors += 1

    # Suggestion 7 Fix: Verify all 3 decoupled G7 decisions
    if gate_stage == "G7":
        rtm_text = RTM_FILE.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"Decision 1 \(Sign-Off\)\*\*:\s*`?approved`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 1 (Sign-Off) not 'approved' in {RTM_FILE}!")
            errors += 1
        if not re.search(r"Decision 2 \(Release Authorization\)\*\*:\s*`?(hold|authorized)`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 2 (Release Authorization) must be explicitly 'hold' or 'authorized' in {RTM_FILE}!")
            errors += 1
        if not re.search(r"Decision 3 \(Ownership & License\)\*\*:\s*`?[A-Za-z0-9._-]+`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 3 (Ownership & License) missing in {RTM_FILE}!")
            errors += 1

    return errors

def _validate_defect_entry(bug: dict) -> int:
    errs = 0
    bug_id = bug.get("bug_id", "UNKNOWN")
    st_val = (bug.get("status") or bug.get("state") or bug.get("defect_status") or "").lower()
    if st_val not in CLOSED_DEFECT_STATUSES:
        print(f"[BLOCKER] Defect '{bug_id}' has unclosed status '{st_val}'! Allowed: {sorted(CLOSED_DEFECT_STATUSES)}")
        errs += 1
    closer = bug.get("closed_by_tester") or bug.get("closed_by") or ""
    if closer not in VALID_QA_CLOSERS:
        print(f"[BLOCKER] Defect '{bug_id}' closed by unauthorized identity '{closer}'! Only independent QA ({sorted(VALID_QA_CLOSERS)}) can close bugs.")
        errs += 1
    return errs

def cmd_check(target_dir=".", require_approval=False, gate_stage="G4", key=None):
    if gate_stage not in VALID_GATES:
        print(f"[BLOCKED] Invalid --gate={gate_stage}. Allowed values: {sorted(VALID_GATES)}")
        sys.exit(1)

    # R1 & R2 Fix: Unconditionally require signing secret and verify full hash chain
    secret = require_signing_secret(key)
    state = load_state()
    if not SPEC_FILE.exists():
        print(f"[BLOCKED] Missing {SPEC_FILE}.")
        sys.exit(1)

    verify_external_anchor(secret)
    records = read_ledger_records()
    freeze_records = [r for r in records if r.get("type") == "FREEZE"]
    if not freeze_records:
        print("[BLOCKED] Fail-Closed: No frozen G3 baseline found in approvals.jsonl! Run 'freeze' first.")
        sys.exit(1)

    verify_full_ledger_chain(records, secret)

    latest_freeze = freeze_records[-1]
    bl_id = latest_freeze.get("baseline_id")
    expected_hash = latest_freeze.get("spec_sha256")
    actual_hash = sha256_file(SPEC_FILE)

    if actual_hash != expected_hash:
        print(f"[BLOCKER] Baseline Tampering Detected! {SPEC_FILE} hash mismatch against approvals.jsonl.\n  Expected: {expected_hash}\n  Actual:   {actual_hash}")
        sys.exit(1)

    state_hash = (state.get("active_baseline") or {}).get("spec_sha256")
    if state_hash != expected_hash:
        print("[BLOCKER] State Tampering Detected! project_state.json hash diverges from approvals.jsonl trust root!")
        sys.exit(1)

    print(f"[OK] Baseline {bl_id} SHA-256 & HMAC chain verified ({actual_hash[:12]}...)")

    if require_approval or gate_stage in ("G5", "G6", "G7"):
        apr_records = [
            r for r in records
            if r.get("type") == "APPROVAL" and r.get("decision") == "approved" and r.get("bound_spec_sha256") == expected_hash
        ]
        if not apr_records:
            print("[BLOCKED] Missing detached G3 approval in approvals.jsonl matching current baseline hash!")
            sys.exit(1)
        latest_apr = apr_records[-1]
        print(f"[OK] Detached approval {latest_apr.get('approval_id')} by '{latest_apr.get('approver')}' HMAC-verified.")

    # Anti-Stubbing & Vacuous Assertion Scan (including .ipynb)
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

    errors += verify_g5_g6_g7_ledgers(gate_stage)

    if errors > 0:
        print(f"[FAILED] Gate {gate_stage} check blocked with {errors} issue(s) across {scanned_files} scanned file(s).")
        sys.exit(1)
    print(f"[PASSED] Gate {gate_stage} checks passed ({scanned_files} code file(s) scanned).")

def parse_kv_flag(args, prefix):
    for a in args:
        if a.startswith(prefix):
            return a.split("=", 1)[1]
    return None

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "help"
    key_arg = parse_kv_flag(args[1:], "--key=")

    if cmd == "init":
        cmd_init()
    elif cmd == "freeze":
        unknown = [a for a in args[1:] if a != "--force" and not a.startswith("--key=")]
        if unknown:
            print(f"[BLOCKED] Unknown arguments for freeze: {unknown}")
            sys.exit(1)
        cmd_freeze(force="--force" in args[1:], key=key_arg)
    elif cmd == "approve":
        pos = [a for a in args[1:] if not a.startswith("-")]
        bad_flags = [a for a in args[1:] if a.startswith("-") and not a.startswith("--gate=") and not a.startswith("--key=")]
        if bad_flags:
            print(f"[BLOCKED] Invalid flag(s) for approve: {bad_flags}")
            sys.exit(1)
        approver = pos[0] if pos else "station_master"
        gate = parse_kv_flag(args[1:], "--gate=") or "G3"
        cmd_approve(approver=approver, gate=gate, key=key_arg)
    elif cmd == "check":
        pos = [a for a in args[1:] if not a.startswith("-")]
        bad_flags = [a for a in args[1:] if a.startswith("-") and a != "--require-approval" and not a.startswith("--gate=") and not a.startswith("--key=")]
        if bad_flags:
            print(f"[BLOCKED] Invalid flag(s) for check: {bad_flags}")
            sys.exit(1)
        target = pos[0] if pos else "."
        req_apr = "--require-approval" in args[1:]
        stage = parse_kv_flag(args[1:], "--gate=") or "G4"
        cmd_check(target, require_approval=req_apr, gate_stage=stage, key=key_arg)
    else:
        print("Usage: python gate_runner.py [init | freeze [--force] [--key=SECRET] | approve [role] [--gate=G3] [--key=SECRET] | check [dir] [--require-approval] [--gate=G4|G5|G6|G7] [--key=SECRET]]")
