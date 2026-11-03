#!/usr/bin/env python3
"""
O9-RD Verifiable Minimal Control Plane CLI (gate_runner.py v1.6)
Hardened against A1-A19 Red-Team Scenarios:
- C-01/C-02/A1/A16: `init` NEVER deletes external trust anchor; missing anchor when ledger is non-empty is FAIL-CLOSED.
- C-03/A2/A10b: Monotonic sequence (`seq`) & key-fingerprint pinned in anchor; enforced by default in `check`.
- C-04/D-8: Evaluates `exit_code` of the LATEST test run per run_id block, preserving historical failure records.
- C-05/C-06/C-07/A4/A5/A6/A12: UTF-16 BOM sniffing, case-insensitive stub scan (TODO_1/FIXME2/pass-only/assert True,msg/assert x==x), scans `tests/` (except self), fails on 0 scanned files unless `--allow-empty-scan`.
- C-08/D-7/A7/A18: Scans bug blocks regardless of top-level YAML key rename (`open_defects:`); removes `rejected` from closed whitelist; `close-bug` requires bug to exist in YAML first (blocks phantom pre-signing).
- C-09/A11b: Cross-platform inter-process file locking (.lock directory spinlock) prevents concurrent write loss.
- C-10/A14: Minimum signing secret length raised to 16 chars.
- C-11/A9b: Strict `isinstance(rec, dict)` validation prevents AttributeError crash on `[]` JSON lines.
- A15 & G6 Prose Fix: Resolves paths relative to repo root; G6 RTM parser only inspects markdown table rows (`|`), ignoring prose notes.
V1.6 additions (declared in docs/CONTROL-MATRIX.md, now actually implemented):
- V1.6/G1-01: `freeze` refuses an empty `spec_and_contracts.md` or one lacking structured `AC-xxx` table rows.
- V1.6/G3-01: `freeze` / `approve` / `check` compute and verify a composite `manifest_sha256` over `spec_and_contracts.md`
  plus every file under `o9_workspace/contracts/`, so any post-freeze byte change anywhere in the baseline circuit-breaks.
- V1.6/G3-03: `.o9_project_id` plus the local registry `~/.o9-trust/index.tsv` pin the workspace <-> project binding, and the
  new `trust-reset` subcommand is the sanctioned, signing-secret-gated escape hatch for a lost/bricked external anchor (R11b).
- V1.6/G5-02: `evidence_log_ref` must resolve inside the repository root (absolute paths and `..` escapes are blocked) and the
  latest QA run is selected by `recorded_at` chronology instead of file order.
- V1.6/G5-03: defect and QA-run blocks are parsed order-independently (any key order, any parent key name).
"""
import sys
import os
import time
import stat
import json
import hmac
import shutil
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

VERSION = "O9-RD-Next-V1.6"

def resolve_workspace() -> Path:
    return Path("o9_workspace").resolve()

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

VALID_GATES = {"G3", "G4", "G5", "G6", "G7"}
VALID_APPROVERS = {"station_master", "qa_lead", "ci_bot", "Over9rowth", "HumanOwner"}
VALID_QA_CLOSERS = {"qa_lead", "independent_qa", "QA-SESSION-01", "station_master"}
CLOSED_DEFECT_STATUSES = {"closed", "verified"}  # D-7 Fix: removed 'rejected'

# --- V1.6 control-plane artifact names -------------------------------------
PROJECT_ID_FILE = ".o9_project_id"     # G3-03: local workspace <-> project binding
TRUST_INDEX_NAME = "index.tsv"         # G3-03: local registry inside ~/.o9-trust/
CONTRACTS_DIR = "contracts"            # G3-01: interface contract files folded into the manifest
BASELINE_SPEC_FILE = "spec_and_contracts.md"

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".go", ".rs",
    ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".sh", ".kt", ".swift", ".ipynb"
}
# A6 Fix: removed 'tests' from SKIP_DIRS so production stubs hidden in tests/ are caught (test_gate_runner.py is excluded by filename)
SKIP_DIRS = {".git", "o9_workspace", "docs", "prompts", "templates", "__pycache__", "node_modules", ".venv"}
SELF_TEST_FILES = {"test_gate_runner.py", "test_v16_controls.py", "redteam.py", "redteam2.py", "confirm.py"}

DEFAULT_STATE_JSON = {
    "project_id": "PRJ-2026-001",
    "sop_version": VERSION,
    "route": "M",
    "state": {"phase": "G0", "execution_state": "active", "gate_results": {}},
    "active_baseline": {
        "baseline_id": None,
        "parent_baseline_id": None,
        "spec_sha256": None,
        "manifest_sha256": None,
        "files": [],
        "frozen_at": None
    },
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
    recorded_at: "2026-11-03T00:00:00Z"
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

def read_text_auto_encoding(filepath: Path) -> str:
    """C-07 / A12 Fix: Sniffs UTF-16 BOMs so UTF-16 encoded stubs cannot evade regex scanning."""
    raw = filepath.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="ignore")
    # Also detect null-byte interleaved UTF-16 without BOM
    if b"\x00" in raw[:100]:
        try:
            return raw.decode("utf-16-le", errors="ignore")
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")

def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def compute_hmac(secret: str, payload: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

def compute_key_fp(secret: str) -> str:
    return hashlib.sha256(f"O9-KEY-FP-V1:{secret}".encode("utf-8")).hexdigest()[:24]

def require_signing_secret(explicit_key: str = None) -> str:
    """C-10 / A14 Fix: Minimum key length raised to 16 chars; zero default fallback."""
    secret = explicit_key or os.environ.get("O9_APPROVAL_SECRET")
    if not secret or len(secret.strip()) < 16:
        print(
            "[BLOCKED] No valid signing key configured (minimum 16 chars required). "
            "Set environment variable O9_APPROVAL_SECRET or pass --key=SECRET."
        )
        sys.exit(1)
    return secret.strip()

@contextmanager
def workspace_lock(ws: Path):
    """C-09 / A11b Fix: Cross-platform atomic directory lock to serialize concurrent ledger writes."""
    lock_dir = ws / ".o9_ledger.lock"
    deadline = time.time() + 10.0
    acquired = False
    while time.time() < deadline:
        try:
            os.mkdir(lock_dir)
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.02)
    if not acquired:
        print("[BLOCKED] Timeout waiting for workspace ledger lock (.o9_ledger.lock)!")
        sys.exit(1)
    try:
        yield
    finally:
        try:
            os.rmdir(lock_dir)
        except Exception:
            pass

def get_external_anchor_path(ws: Path) -> Path:
    ws_abs = str(ws.resolve())
    ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
    trust_dir = Path.home() / ".o9-trust"
    try:
        trust_dir.mkdir(mode=0o700, exist_ok=True)
    except Exception:
        pass
    return trust_dir / f"anchor_{ws_id}.sha256"

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

def sync_external_anchor(ws: Path, secret: str, seq: int):
    apr_log = ws / "approvals.jsonl"
    if not apr_log.exists():
        return
    ledger_hash = sha256_file(apr_log)
    key_fp = compute_key_fp(secret)
    anchor_file = get_external_anchor_path(ws)

    # S1 & A10b Protection: If anchor already exists, enforce key_fp match and monotonic seq
    if anchor_file.exists():
        try:
            parts = anchor_file.read_text(encoding="utf-8").strip().split(":")
            if len(parts) >= 3:
                old_fp = parts[2]
                old_seq = int(parts[3]) if len(parts) >= 4 else 0
                if old_fp != key_fp:
                    print("[BLOCKER] Signing key fingerprint mismatch against pinned external trust anchor!")
                    sys.exit(1)
                if seq < old_seq:
                    print(f"[BLOCKER] Rollback detected! Ledger seq ({seq}) is older than anchored seq ({old_seq}).")
                    sys.exit(1)
        except SystemExit:
            raise
        except Exception:
            print("[BLOCKER] Existing external trust anchor is corrupted!")
            sys.exit(1)

    anchor_mac = compute_hmac(secret, f"ANCHOR:{ledger_hash}:{key_fp}:{seq}")
    try:
        if anchor_file.exists():
            set_writable(anchor_file)
        anchor_file.write_text(f"{ledger_hash}:{anchor_mac}:{key_fp}:{seq}\n", encoding="utf-8")
        set_readonly(anchor_file)
    except Exception as e:
        print(f"[BLOCKED] Failed to write external trust anchor: {e}")
        sys.exit(1)

def verify_external_anchor(ws: Path, secret: str, records: list, expected_fp: str = None):
    """C-02 / A1 / A2 / A10b Fix: Fail-closed when anchor is missing while ledger/project is active."""
    anchor_file = get_external_anchor_path(ws)
    key_fp = compute_key_fp(secret)
    if expected_fp and key_fp != expected_fp:
        print(f"[BLOCKER] Key fingerprint '{key_fp}' does not match --expect-key-fp '{expected_fp}'!")
        sys.exit(1)

    if not anchor_file.exists():
        if records:
            print("[BLOCKER] Fail-Closed (C-02): External trust anchor (~/.o9-trust/) is missing while approvals.jsonl is non-empty! Suspected anchor deletion attack.")
            sys.exit(1)
        return

    try:
        raw = anchor_file.read_text(encoding="utf-8").strip()
        parts = raw.split(":")
        expected_ledger_hash, expected_mac, pinned_fp = parts[0], parts[1], parts[2]
        pinned_seq = int(parts[3]) if len(parts) >= 4 else len(records)
    except Exception:
        print("[BLOCKER] External trust anchor corrupted!")
        sys.exit(1)

    if key_fp != pinned_fp:
        print("[BLOCKER] Signing key fingerprint mismatch against pinned external trust root!")
        sys.exit(1)

    if len(records) < pinned_seq:
        print(f"[BLOCKER] Rollback/Truncation Detected! Ledger has {len(records)} record(s), but external anchor requires >= {pinned_seq}.")
        sys.exit(1)

    apr_log = ws / "approvals.jsonl"
    actual_ledger_hash = sha256_file(apr_log) if apr_log.exists() else ""
    if actual_ledger_hash != expected_ledger_hash:
        print("[BLOCKER] Ledger Tampering or Rollback Detected! approvals.jsonl diverges from external trust anchor (~/.o9-trust/)!")
        sys.exit(1)

    if compute_hmac(secret, f"ANCHOR:{actual_ledger_hash}:{pinned_fp}:{pinned_seq}") != expected_mac:
        print("[BLOCKER] External trust anchor HMAC mismatch! Forged anchor detected.")
        sys.exit(1)

def read_ledger_records(ws: Path) -> list:
    apr_log = ws / "approvals.jsonl"
    if not apr_log.exists():
        return []
    records = []
    with open(apr_log, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[BLOCKER] Corrupted JSON at line #{idx} in approvals.jsonl!")
                    sys.exit(1)
                # C-11 / A9b Fix: Ensure record is a JSON object (dict), never a list/primitive
                if not isinstance(rec, dict):
                    print(f"[BLOCKER] Non-object JSON record at line #{idx} in approvals.jsonl!")
                    sys.exit(1)
                records.append(rec)
    return records

def append_ledger_record(ws: Path, record: dict, secret: str, seq: int):
    apr_log = ws / "approvals.jsonl"
    if apr_log.exists():
        set_writable(apr_log)
    with open(apr_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    set_readonly(apr_log)
    sync_external_anchor(ws, secret, seq)

def load_state(ws: Path) -> dict:
    state_file = ws / "project_state.json"
    if not state_file.exists():
        print(f"[BLOCKED] Missing {state_file}. Run: python gate_runner.py init")
        sys.exit(1)
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("Root must be a JSON object")
        return state
    except Exception as e:
        print(f"[BLOCKED] Corrupted JSON in {state_file}: {e}")
        sys.exit(1)

def save_state(ws: Path, state: dict):
    state_file = ws / "project_state.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------------------
# V1.6 primitives: ordered-independent YAML parsing, structured AC parsing,
# composite manifest (G3-01) and the local project registry (G3-03).
# ---------------------------------------------------------------------------

def parse_kv_line(text: str):
    """Parses one `key: value` YAML scalar line into (lower_key, unquoted_value)."""
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*:\s*(.*)$", text)
    if not m:
        return None
    key = m.group(1).strip().lower()
    val = m.group(2).strip()
    if " #" in val and not (val.startswith("'") or val.startswith('"')):
        val = val.split(" #", 1)[0].strip()
    return key, val.strip().strip("'\"")

def extract_yaml_items(yaml_text: str, id_key: str) -> list:
    """V1.6 / G5-03: Order-independent list-item extractor.

    Collects every YAML list item (`- key: value`) together with all of its sibling
    `key: value` lines, regardless of the ORDER in which the keys appear and
    regardless of the parent key name (`defects:`, `open_defects:`, `g5_test_runs:` ...).
    Only items carrying `id_key` are returned.
    """
    items, cur, cur_indent = [], None, None
    for raw in yaml_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        m_item = re.match(r"^-\s+(.*)$", stripped)
        if m_item:
            if cur is not None:
                items.append(cur)
            cur, cur_indent = {}, indent
            kv = parse_kv_line(m_item.group(1))
            if kv:
                cur[kv[0]] = kv[1]
            continue
        if cur is None:
            continue
        if indent <= cur_indent:
            items.append(cur)
            cur = None
            continue
        kv = parse_kv_line(stripped)
        if kv and kv[0] not in cur:
            cur[kv[0]] = kv[1]
    if cur is not None:
        items.append(cur)
    return [it for it in items if it.get(id_key)]

def parse_timestamp(value):
    """Parses an ISO-8601 timestamp; returns None when unparseable."""
    if value is None:
        return None
    txt = str(value).strip().strip("'\"")
    if not txt:
        return None
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(txt)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def select_latest_g5_run(runs: list):
    """V1.6 / G5-02: Select the chronologically latest QA run by `recorded_at`.

    Falls back to document order only when no run declares `recorded_at`
    (legacy v1.5 workspaces).
    """
    if not runs:
        return None
    stamped = [(parse_timestamp(r.get("recorded_at")), idx, r) for idx, r in enumerate(runs)]
    usable = [t for t in stamped if t[0] is not None]
    if usable:
        return max(usable, key=lambda t: (t[0], t[1]))[2]
    return runs[-1]

def spec_ac_rows(spec_text: str) -> list:
    """V1.6 / G1-01: Structured `AC-xxx` rows are markdown table rows only."""
    return [
        line for line in spec_text.splitlines()
        if line.strip().startswith("|") and re.search(r"\bAC-\d+\b", line)
    ]

def verify_spec_structure(spec_file: Path) -> int:
    """V1.6 / G1-01: the spec must be non-empty and carry structured `AC-xxx` rows."""
    if not spec_file.exists():
        print(f"[BLOCKED] Missing {spec_file}.")
        return 1
    text = spec_file.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        print(f"[BLOCKER] G1-01 Violation: {spec_file.name} is empty.")
        return 1
    rows = spec_ac_rows(text)
    if not rows:
        print(f"[BLOCKER] G1-01 Violation: {spec_file.name} contains no structured `AC-xxx` table rows.")
        return 1
    print(f"[OK] G1-01: {spec_file.name} is non-empty and carries {len(rows)} structured `AC-xxx` row(s).")
    return 0

def collect_baseline_files(ws: Path) -> list:
    """V1.6 / G3-01: the immutable baseline = spec + every interface contract file."""
    targets = []
    spec = ws / BASELINE_SPEC_FILE
    if spec.is_file():
        targets.append(spec)
    contracts = ws / CONTRACTS_DIR
    if contracts.is_dir():
        targets.extend(sorted(p for p in contracts.rglob("*") if p.is_file()))
    entries = []
    for path in targets:
        try:
            rel = path.relative_to(ws.parent).as_posix()
        except ValueError:
            rel = path.as_posix()
        entries.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    entries.sort(key=lambda e: e["path"])
    return entries

def manifest_root(files: list) -> str:
    """V1.6 / G3-01: composite SHA-256 over the canonical manifest payload."""
    canonical = json.dumps(
        [{"path": f["path"], "bytes": f["bytes"], "sha256": f["sha256"]} for f in files],
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def build_manifest(ws: Path):
    """V1.6 / G3-01: returns (files, composite manifest_sha256)."""
    files = collect_baseline_files(ws)
    return files, manifest_root(files)

def describe_manifest_diff(expected_files: list, current_files: list) -> list:
    """Human-readable list of added/removed/modified baseline artifacts."""
    exp = {f.get("path"): f.get("sha256") for f in (expected_files or [])}
    cur = {f.get("path"): f.get("sha256") for f in (current_files or [])}
    changes = []
    for path in sorted(set(exp) | set(cur)):
        if path not in cur:
            changes.append(f"deleted: {path}")
        elif path not in exp:
            changes.append(f"unregistered: {path}")
        elif exp[path] != cur[path]:
            changes.append(f"modified: {path}")
    return changes

def get_trust_dir() -> Path:
    trust_dir = Path.home() / ".o9-trust"
    try:
        trust_dir.mkdir(mode=0o700, exist_ok=True)
    except Exception:
        pass
    return trust_dir

def get_trust_index_path() -> Path:
    return get_trust_dir() / TRUST_INDEX_NAME

def read_trust_index() -> list:
    """V1.6 / G3-03: reads the local workspace <-> project registry."""
    idx = get_trust_index_path()
    rows = []
    if not idx.exists():
        return rows
    try:
        for line in idx.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            rows.append({
                "ws_id": parts[0], "workspace": parts[1], "project_id": parts[2],
                "key_fp": parts[3], "seq": parts[4], "updated_at": parts[5],
            })
    except Exception:
        return rows
    return rows

def upsert_trust_index(ws: Path, project_id: str, key_fp: str = "", seq: int = 0):
    """V1.6 / G3-03: records/refreshes this workspace entry in `index.tsv`.

    Updates the row for this workspace IN PLACE and preserves any pre-existing
    or legacy rows verbatim, so the registry never destroys unrelated history.
    """
    ws_abs = str(ws.resolve())
    ws_id = hashlib.sha256(ws_abs.encode("utf-8")).hexdigest()[:16]
    idx = get_trust_index_path()
    lines = []
    if idx.exists():
        try:
            lines = idx.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            lines = []
    new_line = "\t".join([ws_id, ws_abs, project_id, key_fp or "", str(seq), now_iso()])
    out, replaced = [], False
    for line in lines:
        fields = line.split("\t")
        if line.strip() and not line.startswith("#") and fields[0] == ws_id:
            if not replaced:
                out.append(new_line)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(new_line)
    if not any(l.startswith("#") for l in out):
        out.insert(0, "# O9-RD local trust registry: ws_id<TAB>workspace<TAB>project_id<TAB>key_fp<TAB>seq<TAB>updated_at")
    try:
        if idx.exists():
            set_writable(idx)
        idx.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception as e:
        # The authoritative trust root is still the HMAC anchor + ledger chain; the
        # local registry is defence-in-depth, so degrade loudly instead of bricking init.
        print(f"[WARN] Could not update local registry {TRUST_INDEX_NAME}: {e}")

def read_project_id_file(ws: Path):
    """V1.6 / G3-03: reads `.o9_project_id` (None when absent/corrupt)."""
    pid_file = ws / PROJECT_ID_FILE
    if not pid_file.exists():
        return None
    try:
        meta = json.loads(pid_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    return meta if isinstance(meta, dict) else None

def ensure_project_id(ws: Path, project_id: str) -> dict:
    """V1.6 / G3-03: creates `.o9_project_id` once and never silently re-binds it."""
    meta = read_project_id_file(ws) or {}
    if not meta.get("project_id"):
        meta = {"project_id": project_id, "workspace": str(ws.resolve()), "created_at": now_iso()}
        try:
            set_writable(ws / PROJECT_ID_FILE)
        except Exception:
            pass
        (ws / PROJECT_ID_FILE).write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta

def cmd_trust_reset(confirm_token: str, key=None):
    """V1.6 / G3-03: sanctioned escape hatch for a lost or bricked external trust anchor.

    Closes the R11b dead-end of v1.5 (deleting `o9_workspace` used to brick a project
    permanently with no `trust-reset`). It still cannot be used by an agent on its own:
    it requires the human-held signing secret (>= 16 chars) AND the exact project_id as
    an explicit confirmation token, and it ARCHIVES the old anchor/ledger instead of
    silently deleting them.
    """
    secret = require_signing_secret(key)
    ws = resolve_workspace()

    # V1.6 / G3-03: identify the project even when the whole workspace was wiped.
    # Source 1: `.o9_project_id`; source 2: the local `index.tsv` registry — this is
    # exactly why the registry exists: it survives deletion of `o9_workspace/`.
    meta = read_project_id_file(ws) or {}
    project_id = meta.get("project_id")
    if not project_id:
        ws_abs = str(ws.resolve())
        for row in read_trust_index():
            if row.get("workspace") == ws_abs and row.get("project_id"):
                project_id = row["project_id"]
                break
    if not project_id:
        print(
            f"[BLOCKED] Cannot determine the project_id: {PROJECT_ID_FILE} is missing and no "
            f"'{TRUST_INDEX_NAME}' entry exists for {ws.resolve()}. Run 'init' first."
        )
        sys.exit(1)
    if confirm_token != project_id:
        print(f"[BLOCKED] Confirmation token mismatch! Re-run as: python gate_runner.py trust-reset {project_id} --key=SECRET")
        sys.exit(1)

    ws.mkdir(exist_ok=True)
    with workspace_lock(ws):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        apr_log = ws / "approvals.jsonl"
        anchor_file = get_external_anchor_path(ws)
        archived = []

        if anchor_file.exists():
            set_writable(anchor_file)
            anchor_bak = anchor_file.with_name(f"{anchor_file.name}.bak.{stamp}")
            anchor_file.replace(anchor_bak)
            archived.append(anchor_bak.name)

        if apr_log.exists():
            # The ledger is kept read-only by design; it must be made writable before it can
            # be archived or truncated (Linux 0444 and the Windows read-only attribute both
            # refuse the write outright).
            set_writable(apr_log)
            if apr_log.stat().st_size > 0:
                ledger_bak = apr_log.with_name(f"{apr_log.name}.bak.{stamp}")
                apr_log.replace(ledger_bak)
                archived.append(ledger_bak.name)

        apr_log.write_text("", encoding="utf-8")
        set_readonly(apr_log)

        # A fully wiped workspace gets fresh control-plane state instead of an error.
        if (ws / "project_state.json").exists():
            state = load_state(ws)
        else:
            state = json.loads(json.dumps(DEFAULT_STATE_JSON))
            state["project_id"] = project_id
        active = state.get("active_baseline") or {}
        if active.get("baseline_id"):
            state.setdefault("baseline_history", []).append(active)
        state["active_baseline"] = {
            "baseline_id": None, "parent_baseline_id": None,
            "spec_sha256": None, "manifest_sha256": None,
            "files": [], "frozen_at": None
        }
        state.setdefault("state", {})["phase"] = "G0"
        state.setdefault("audit_events", []).append({
            "at": now_iso(),
            "action": "trust_reset",
            "project_id": project_id,
            "archived": archived,
            "key_fp": compute_key_fp(secret),
        })
        save_state(ws, state)
        ensure_project_id(ws, project_id)
        upsert_trust_index(ws, project_id, compute_key_fp(secret), 0)
        print(f"[TRUST RESET] Project '{project_id}': archived {archived if archived else 'nothing'} and re-established an empty trust root.")
        print("[NEXT] Run 'init' (if the workspace was wiped) then 'freeze' to create a fresh, newly signed baseline.")

def cmd_init():
    """C-01 / A16 Fix: `init` NEVER deletes an existing external trust anchor!"""
    ws = resolve_workspace()
    anchor_file = get_external_anchor_path(ws)
    apr_log = ws / "approvals.jsonl"

    # If external anchor already exists, block re-init if ledger was wiped/truncated
    if anchor_file.exists():
        if not apr_log.exists() or apr_log.stat().st_size == 0:
            print("[BLOCKER] Security Violation (C-01/A16): External trust anchor already exists for this workspace, but approvals.jsonl is empty/missing! Refusing to reset trust anchor via 'init'.")
            sys.exit(1)

    ws.mkdir(exist_ok=True)
    (ws / "evidence").mkdir(exist_ok=True)
    fallbacks = {
        "project_state.json": json.dumps(DEFAULT_STATE_JSON, indent=2, ensure_ascii=False),
        "spec_and_contracts.md": DEFAULT_SPEC_MD,
        "review_and_defects.yaml": DEFAULT_REVIEW_YAML,
        "rtm_acceptance.md": DEFAULT_RTM_MD,
    }
    for fname, fallback_content in fallbacks.items():
        dst = ws / fname
        src = TEMPLATES_DIR / fname
        if not dst.exists():
            if src.exists():
                shutil.copyfile(src, dst)
            else:
                dst.write_text(fallback_content, encoding="utf-8")
    ev_log = ws / "evidence" / "run-bb-001.log"
    if not ev_log.exists():
        ev_log.write_text("[G5 Black-Box Test Run Log] Initialized evidence artifact.\n", encoding="utf-8")
    if not apr_log.exists():
        apr_log.write_text("", encoding="utf-8")
        set_readonly(apr_log)

    state = load_state(ws)
    state["sop_version"] = VERSION

    # V1.6 / G3-03: pin the workspace <-> project binding locally (`index.tsv` + `.o9_project_id`)
    existing_meta = read_project_id_file(ws) or {}
    project_id = existing_meta.get("project_id") or state.get("project_id") or DEFAULT_STATE_JSON["project_id"]
    ws_abs = str(ws.resolve())
    for row in read_trust_index():
        if row.get("workspace") == ws_abs and row.get("project_id") and row["project_id"] != project_id:
            print(f"[BLOCKER] Local registry ({TRUST_INDEX_NAME}) binds this workspace to project '{row['project_id']}', but the workspace now declares '{project_id}'. Refusing accidental re-binding; use 'trust-reset' for an intentional reset.")
            sys.exit(1)
    ensure_project_id(ws, project_id)
    state["project_id"] = project_id

    state.setdefault("baseline_history", [])
    state.setdefault("audit_events", []).append({"at": now_iso(), "action": "init_workspace"})
    save_state(ws, state)
    upsert_trust_index(ws, project_id, "", 0)
    print(f"[OK] Initialized O9-RD workspace ({VERSION}) in ./{ws.name}/ (project_id={project_id})")

def verify_full_ledger_chain(records: list, secret: str):
    prev_hmac = "GENESIS"
    for idx, rec in enumerate(records, 1):
        rtype = rec.get("type")
        seq = rec.get("seq", idx)
        if seq != idx:
            print(f"[BLOCKER] Ledger sequence number mismatch at record #{idx} (expected seq={idx}, got {seq})!")
            sys.exit(1)
        if rec.get("prev_hmac", "GENESIS") != prev_hmac:
            print(f"[BLOCKER] Ledger hash-chain broken at record #{idx} in approvals.jsonl!")
            sys.exit(1)
        if rtype == "FREEZE":
            # V1.6 / G3-01: the composite manifest_sha256 is folded into the signed payload.
            # Legacy v1.5 records (no manifest_sha256) stay verifiable via the shorter payload.
            if rec.get("manifest_sha256"):
                payload = f"FREEZE:{seq}:{rec.get('baseline_id')}:{rec.get('spec_sha256')}:{rec.get('manifest_sha256')}:{prev_hmac}"
            else:
                payload = f"FREEZE:{seq}:{rec.get('baseline_id')}:{rec.get('spec_sha256')}:{prev_hmac}"
        elif rtype == "APPROVAL":
            if rec.get("bound_manifest_sha256"):
                payload = f"APPROVAL:{seq}:{rec.get('approval_id')}:{rec.get('gate')}:{rec.get('approver')}:{rec.get('bound_baseline_id')}:{rec.get('bound_spec_sha256')}:{rec.get('bound_manifest_sha256')}:{prev_hmac}"
            else:
                payload = f"APPROVAL:{seq}:{rec.get('approval_id')}:{rec.get('gate')}:{rec.get('approver')}:{rec.get('bound_baseline_id')}:{rec.get('bound_spec_sha256')}:{prev_hmac}"
        elif rtype == "BUG_CLOSE":
            payload = f"BUG_CLOSE:{seq}:{rec.get('bug_id')}:{rec.get('qa_role')}:{rec.get('bound_baseline_id')}:{prev_hmac}"
        else:
            print(f"[BLOCKER] Unknown record type '{rtype}' in approvals.jsonl!")
            sys.exit(1)
        expected_mac = compute_hmac(secret, payload)
        if rec.get("hmac") != expected_mac:
            print(f"[BLOCKER] Forged or unauthorized {rtype} record #{idx} in approvals.jsonl! HMAC verification failed.")
            sys.exit(1)
        prev_hmac = expected_mac

def cmd_freeze(force=False, key=None):
    secret = require_signing_secret(key)
    ws = resolve_workspace()
    spec_file = ws / BASELINE_SPEC_FILE
    state = load_state(ws)
    if not spec_file.exists():
        print(f"[BLOCKED] Missing {spec_file}.")
        sys.exit(1)

    # V1.6 / G1-01: never freeze an empty spec or one without structured AC-xxx rows.
    if verify_spec_structure(spec_file) != 0:
        sys.exit(1)

    with workspace_lock(ws):
        records = read_ledger_records(ws)
        verify_external_anchor(ws, secret, records)
        if records:
            verify_full_ledger_chain(records, secret)

        freeze_records = [r for r in records if r.get("type") == "FREEZE"]
        if freeze_records and not force:
            last_bl = freeze_records[-1].get("baseline_id")
            print(f"[BLOCKED] Baseline {last_bl} already frozen. Use 'freeze --force' with valid signing secret to re-freeze.")
            sys.exit(1)

        digest = sha256_file(spec_file)
        # V1.6 / G3-01: composite manifest across spec + interface contract files.
        manifest_files, manifest_hash = build_manifest(ws)
        next_num = len(freeze_records) + 1
        new_id = f"BL-{next_num:03d}"
        parent_id = freeze_records[-1]["baseline_id"] if freeze_records else None
        prev_hmac = records[-1]["hmac"] if records else "GENESIS"
        seq = len(records) + 1
        ts = now_iso()

        mac = compute_hmac(secret, f"FREEZE:{seq}:{new_id}:{digest}:{manifest_hash}:{prev_hmac}")
        append_ledger_record(ws, {
            "seq": seq,
            "type": "FREEZE",
            "baseline_id": new_id,
            "parent_baseline_id": parent_id,
            "spec_sha256": digest,
            "manifest_sha256": manifest_hash,
            "files": manifest_files,
            "forced": bool(force),
            "prev_hmac": prev_hmac,
            "at": ts,
            "hmac": mac
        }, secret, seq)

        active = state.get("active_baseline") or {}
        if active.get("spec_sha256"):
            state.setdefault("baseline_history", []).append(active)
        state["active_baseline"] = {
            "baseline_id": new_id, "parent_baseline_id": parent_id,
            "spec_sha256": digest, "manifest_sha256": manifest_hash,
            "files": manifest_files, "frozen_at": ts, "forced": bool(force)
        }
        state.setdefault("state", {})["phase"] = "G3"
        save_state(ws, state)
        upsert_trust_index(ws, state.get("project_id") or DEFAULT_STATE_JSON["project_id"], compute_key_fp(secret), seq)
        print(f"[G3 FROZEN] {new_id} (seq={seq}, key_fp={compute_key_fp(secret)}) -> spec SHA-256: {digest}")
        print(f"[G3 FROZEN] manifest_sha256: {manifest_hash} across {len(manifest_files)} baseline file(s): {[f['path'] for f in manifest_files]}")

def cmd_approve(approver="station_master", gate="G3", key=None):
    if approver.startswith("-"):
        print(f"[BLOCKED] Invalid approver name '{approver}'.")
        sys.exit(1)
    if approver not in VALID_APPROVERS:
        print(f"[BLOCKED] Unauthorized approver role '{approver}'. Allowed: {sorted(VALID_APPROVERS)}")
        sys.exit(1)
    if gate not in VALID_GATES:
        print(f"[BLOCKED] Invalid gate '{gate}'. Allowed: {sorted(VALID_GATES)}")
        sys.exit(1)

    secret = require_signing_secret(key)
    ws = resolve_workspace()
    spec_file = ws / BASELINE_SPEC_FILE

    with workspace_lock(ws):
        records = read_ledger_records(ws)
        if not records:
            print("[BLOCKED] Cannot approve: No frozen baseline in approvals.jsonl. Run 'freeze' first.")
            sys.exit(1)
        verify_external_anchor(ws, secret, records)
        verify_full_ledger_chain(records, secret)

        freeze_records = [r for r in records if r.get("type") == "FREEZE"]
        latest_freeze = freeze_records[-1]
        bl_id = latest_freeze["baseline_id"]
        digest = latest_freeze["spec_sha256"]
        bound_manifest = latest_freeze.get("manifest_sha256")

        if not spec_file.exists() or sha256_file(spec_file) != digest:
            print("[BLOCKED] Spec file modified after freeze! Re-freeze before approving.")
            sys.exit(1)

        # V1.6 / G3-01: the whole composite manifest must still match at approval time.
        if bound_manifest:
            cur_files, cur_manifest = build_manifest(ws)
            if cur_manifest != bound_manifest:
                print("[BLOCKED] Baseline manifest modified after freeze! Re-freeze before approving.")
                for change in describe_manifest_diff(latest_freeze.get("files") or [], cur_files):
                    print(f"    - {change}")
                sys.exit(1)

        apr_count = len([r for r in records if r.get("type") == "APPROVAL"]) + 1
        apr_id = f"APR-{gate}-{apr_count:03d}"
        prev_hmac = records[-1]["hmac"]
        seq = len(records) + 1
        ts = now_iso()
        if bound_manifest:
            payload = f"APPROVAL:{seq}:{apr_id}:{gate}:{approver}:{bl_id}:{digest}:{bound_manifest}:{prev_hmac}"
        else:
            payload = f"APPROVAL:{seq}:{apr_id}:{gate}:{approver}:{bl_id}:{digest}:{prev_hmac}"
        mac = compute_hmac(secret, payload)

        record = {
            "seq": seq,
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
        }
        if bound_manifest:
            record["bound_manifest_sha256"] = bound_manifest
        append_ledger_record(ws, record, secret, seq)

        upsert_trust_index(ws, load_state(ws).get("project_id") or DEFAULT_STATE_JSON["project_id"], compute_key_fp(secret), seq)

        state = load_state(ws)
        state.setdefault("state", {})["phase"] = "G4" if gate == "G3" else gate
        save_state(ws, state)
        print(f"[{gate} APPROVED] Detached HMAC record {apr_id} (seq={seq}) by '{approver}' bound to {bl_id}")

def extract_all_defect_entries(yaml_text: str) -> list:
    """C-08 / A7 + V1.6 G5-03: Extracts defect items anywhere in the YAML file.

    Keeps the A7 guarantee (any parent key name, e.g. `open_defects:` is still caught)
    and adds the v1.6 guarantee that keys may appear in ANY order inside an item
    (`status:` before `bug_id:` is parsed identically).
    """
    return extract_yaml_items(yaml_text, "bug_id")

def cmd_close_bug(bug_id: str, qa_role="qa_lead", key=None):
    if not bug_id or bug_id.startswith("-"):
        print("[BLOCKED] Valid BUG_ID required.")
        sys.exit(1)
    if qa_role not in VALID_QA_CLOSERS:
        print(f"[BLOCKED] Unauthorized QA closer role '{qa_role}'. Allowed: {sorted(VALID_QA_CLOSERS)}")
        sys.exit(1)

    secret = require_signing_secret(key)
    ws = resolve_workspace()
    review_file = ws / "review_and_defects.yaml"

    with workspace_lock(ws):
        # A18 Fix: Verify the bug_id actually exists in review_and_defects.yaml before signing its closure!
        if not review_file.exists():
            print(f"[BLOCKED] Missing {review_file}!")
            sys.exit(1)
        existing_bugs = {b.get("bug_id") for b in extract_all_defect_entries(review_file.read_text(encoding="utf-8", errors="ignore"))}
        if bug_id not in existing_bugs:
            print(f"[BLOCKER] Phantom Bug Prevention (A18): Cannot pre-sign closure for non-existent bug '{bug_id}'! Register the defect in {review_file.name} first.")
            sys.exit(1)

        records = read_ledger_records(ws)
        if not records:
            print("[BLOCKED] Cannot close bug: No frozen baseline in approvals.jsonl.")
            sys.exit(1)
        verify_external_anchor(ws, secret, records)
        verify_full_ledger_chain(records, secret)

        freeze_records = [r for r in records if r.get("type") == "FREEZE"]
        bl_id = freeze_records[-1]["baseline_id"]
        prev_hmac = records[-1]["hmac"]
        seq = len(records) + 1
        ts = now_iso()

        payload = f"BUG_CLOSE:{seq}:{bug_id}:{qa_role}:{bl_id}:{prev_hmac}"
        mac = compute_hmac(secret, payload)

        append_ledger_record(ws, {
            "seq": seq,
            "type": "BUG_CLOSE",
            "bug_id": bug_id,
            "qa_role": qa_role,
            "bound_baseline_id": bl_id,
            "prev_hmac": prev_hmac,
            "at": ts,
            "hmac": mac
        }, secret, seq)
        print(f"[BUG CLOSED] Signed BUG_CLOSE (seq={seq}) for '{bug_id}' by '{qa_role}' in approvals.jsonl")

def verify_g5_g6_g7_ledgers(ws: Path, gate_stage: str, records: list) -> int:
    errors = 0
    repo_root = ws.parent
    review_file = ws / "review_and_defects.yaml"
    rtm_file = ws / "rtm_acceptance.md"

    if gate_stage in ("G5", "G6", "G7"):
        if not review_file.exists():
            print(f"[BLOCKER] Fail-Closed: Missing {review_file} required for {gate_stage}!")
            return 1
        content = review_file.read_text(encoding="utf-8", errors="ignore")

        if not re.search(r"source_code_hidden_verified:\s*true", content, re.IGNORECASE):
            print(f"[BLOCKER] {gate_stage} violation: Missing 'source_code_hidden_verified: true' in {review_file.name}!")
            errors += 1

        # A15 Fix: Resolve evidence_log_ref relative to repo_root (not arbitrary CWD)
        ev_refs = re.findall(r"evidence_log_ref:\s*['\"]?([^'\"\n\r#]+)['\"]?", content)
        if not ev_refs:
            print(f"[BLOCKER] Missing 'evidence_log_ref' in {review_file.name}!")
            errors += 1
        try:
            repo_root_resolved = repo_root.resolve()
        except Exception:
            repo_root_resolved = repo_root
        for ref in ev_refs:
            ref_clean = ref.strip()
            if ref_clean in ("/dev/null", "NUL", "null", "none", ""):
                print(f"[BLOCKER] Invalid device/null test evidence path '{ref_clean}'!")
                errors += 1
                continue
            ev_path = Path(ref_clean) if Path(ref_clean).is_absolute() else (repo_root / ref_clean)
            # V1.6 / G5-02: evidence must live INSIDE the repository root (no absolute/`..` escapes).
            try:
                resolved_ev = ev_path.resolve()
                resolved_ev.relative_to(repo_root_resolved)
                inside_repo = True
            except Exception:
                inside_repo = False
            if not inside_repo:
                print(f"[BLOCKER] Evidence path '{ref_clean}' escapes the repository root (G5-02 violation)!")
                errors += 1
                continue
            if not resolved_ev.exists() or not resolved_ev.is_file():
                print(f"[BLOCKER] Missing test evidence file '{ref_clean}'!")
                errors += 1
            elif resolved_ev.stat().st_size == 0:
                print(f"[BLOCKER] Test evidence file '{ref_clean}' is empty (0 bytes)!")
                errors += 1

        # C-04 / D-8 + V1.6 G5-02: evaluate the exit_code of the CHRONOLOGICALLY LATEST run
        # (selected by `recorded_at`), so back-filling an older passing run cannot mask a
        # newer failing one. Falls back to document order for legacy runs without timestamps.
        g5_runs = extract_yaml_items(content, "run_id")
        latest_run = select_latest_g5_run(g5_runs)
        if latest_run is None:
            print(f"[BLOCKER] No 'g5_test_runs' entry found in {review_file.name}!")
            errors += 1
        else:
            raw_code = latest_run.get("exit_code")
            try:
                code_val = int(str(raw_code).strip())
            except Exception:
                code_val = None
            if code_val != 0:
                print(
                    f"[BLOCKER] Latest test run '{latest_run.get('run_id')}' "
                    f"(recorded_at={latest_run.get('recorded_at', 'n/a')}) has non-zero or missing "
                    f"exit_code {raw_code!r} in {review_file.name}!"
                )
                errors += 1

        # C-08 / A7 / S3 Fix: Inspect all defect blocks anywhere in the YAML and require matching BUG_CLOSE signature
        signed_closures = {
            (r.get("bug_id"), r.get("qa_role"))
            for r in records if r.get("type") == "BUG_CLOSE"
        }
        for bug in extract_all_defect_entries(content):
            bug_id = bug.get("bug_id", "UNKNOWN")
            st_val = (bug.get("status") or bug.get("state") or bug.get("defect_status") or "").lower()
            if st_val not in CLOSED_DEFECT_STATUSES:
                print(f"[BLOCKER] Defect '{bug_id}' has unclosed status '{st_val}'! Allowed: {sorted(CLOSED_DEFECT_STATUSES)}")
                errors += 1
            closer = bug.get("closed_by_tester") or bug.get("closed_by") or ""
            if closer not in VALID_QA_CLOSERS:
                print(f"[BLOCKER] Defect '{bug_id}' closed by unauthorized role '{closer}'!")
                errors += 1
            elif (bug_id, closer) not in signed_closures:
                print(f"[BLOCKER] S3 Violation: Defect '{bug_id}' claims closed by '{closer}' in YAML, but has NO cryptographic BUG_CLOSE record in approvals.jsonl!")
                errors += 1

    if gate_stage in ("G6", "G7"):
        if not rtm_file.exists():
            print(f"[BLOCKER] Fail-Closed: Missing {rtm_file} required for {gate_stage}!")
            return errors + 1
        rtm_text = rtm_file.read_text(encoding="utf-8", errors="ignore")
        # Confirm.py Fix: Only check table rows starting with '|' containing AC-IDs, never prose paragraphs!
        ac_rows = [
            line for line in rtm_text.splitlines()
            if line.strip().startswith("|") and re.search(r"\bAC-\d+\b", line)
        ]
        if not ac_rows:
            print(f"[BLOCKER] {rtm_file.name} contains no valid AC traceability table rows!")
            errors += 1
        for row in ac_rows:
            if re.search(r"\b(not-run|failed|blocked|not-covered)\b", row, re.IGNORECASE):
                print(f"[BLOCKER] Unverified or failed AC row in {rtm_file.name}: {row.strip()}")
                errors += 1

    if gate_stage == "G7":
        rtm_text = rtm_file.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"Decision 1 \(Sign-Off\)\*\*:\s*`?approved`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 1 (Sign-Off) not 'approved' in {rtm_file.name}!")
            errors += 1
        if not re.search(r"Decision 2 \(Release Authorization\)\*\*:\s*`?(hold|authorized)`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 2 (Release Authorization) must be 'hold' or 'authorized'!")
            errors += 1
        if not re.search(r"Decision 3 \(Ownership & License\)\*\*:\s*`?[A-Za-z0-9._-]+`?", rtm_text, re.IGNORECASE):
            print(f"[BLOCKER] G7 Decision 3 (Ownership & License) missing!")
            errors += 1

    return errors

def has_pass_only_function(text: str, suffix: str) -> bool:
    """A5 Fix: Detects Python functions/methods whose body is solely `pass` or `...`."""
    if suffix != ".py":
        return False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)def\s+[A-Za-z0-9_]+\s*\(.*\)\s*(->.*)?:\s*$", line)
        if m:
            indent = len(m.group(1))
            body = []
            for j in range(i + 1, len(lines)):
                s = lines[j].strip()
                if not s or s.startswith("#"):
                    continue
                cur_indent = len(lines[j]) - len(lines[j].lstrip())
                if cur_indent <= indent:
                    break
                body.append(s)
            if body == ["pass"] or body == ["..."]:
                return True
    return False

def cmd_check(target_dir=".", require_approval=False, gate_stage="G4", key=None, expected_fp=None, allow_empty_scan=False):
    if gate_stage not in VALID_GATES:
        print(f"[BLOCKED] Invalid --gate={gate_stage}. Allowed: {sorted(VALID_GATES)}")
        sys.exit(1)

    secret = require_signing_secret(key)
    # If target_dir contains o9_workspace, anchor workspace to target_dir; otherwise current dir
    cand_ws = (Path(target_dir) / "o9_workspace").resolve()
    ws = cand_ws if cand_ws.exists() else resolve_workspace()
    spec_file = ws / BASELINE_SPEC_FILE
    state = load_state(ws)
    if not spec_file.exists():
        print(f"[BLOCKED] Missing {spec_file}.")
        sys.exit(1)

    records = read_ledger_records(ws)
    freeze_records = [r for r in records if r.get("type") == "FREEZE"]
    if not freeze_records:
        print("[BLOCKED] Fail-Closed: No frozen G3 baseline found in approvals.jsonl! Run 'freeze' first.")
        sys.exit(1)

    env_fp = expected_fp or os.environ.get("O9_EXPECTED_KEY_FP")
    verify_external_anchor(ws, secret, records, expected_fp=env_fp)
    verify_full_ledger_chain(records, secret)

    latest_freeze = freeze_records[-1]
    bl_id = latest_freeze.get("baseline_id")
    expected_hash = latest_freeze.get("spec_sha256")
    actual_hash = sha256_file(spec_file)

    if actual_hash != expected_hash:
        print(f"[BLOCKER] Baseline Tampering Detected! {spec_file.name} hash mismatch against approvals.jsonl.")
        sys.exit(1)

    state_hash = (state.get("active_baseline") or {}).get("spec_sha256")
    if state_hash != expected_hash:
        print("[BLOCKER] State Tampering Detected! project_state.json hash diverges from approvals.jsonl trust root!")
        sys.exit(1)

    print(f"[OK] Baseline {bl_id} SHA-256, monotonic seq & HMAC chain verified ({actual_hash[:12]}...)")

    # V1.6 / G3-01: verify the composite manifest over spec + interface contract files.
    expected_manifest = latest_freeze.get("manifest_sha256")
    if expected_manifest:
        cur_files, cur_manifest = build_manifest(ws)
        if cur_manifest != expected_manifest:
            print("[BLOCKER] Baseline Manifest Tampering Detected! manifest_sha256 mismatch against approvals.jsonl.")
            for change in describe_manifest_diff(latest_freeze.get("files") or [], cur_files):
                print(f"    - {change}")
            sys.exit(1)
        state_manifest = (state.get("active_baseline") or {}).get("manifest_sha256")
        if state_manifest != expected_manifest:
            print("[BLOCKER] State Tampering Detected! project_state.json manifest_sha256 diverges from approvals.jsonl trust root!")
            sys.exit(1)
        print(f"[OK] Composite manifest_sha256 verified ({cur_manifest[:12]}... across {len(cur_files)} baseline file(s))")

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

    # C-06 / A5 Fix: Case-insensitive stub scan (catches todo, TODO_1, FIXME2) & broad vacuous assert scan
    stub_re = re.compile(r"(?<![A-Za-z])(TODO|FIXME|XXX|HACK)(?![A-Za-z])", re.IGNORECASE)
    vacuous_assert_re = re.compile(
        r"(?:^\s*assert\s+(?:True|1)\b|assertTrue\s*\(\s*True\b|expect\s*\(\s*true\s*\)\.toBe\s*\(\s*true\s*\)|^\s*assert\s+([A-Za-z0-9_]+)\s*==\s*\1\b)"
    )
    errors = 0
    scanned_files = 0

    target_path = Path(target_dir).resolve()
    self_path = Path(__file__).resolve()

    for root, _, files in os.walk(target_path):
        root_parts = set(Path(root).relative_to(target_path).parts) if Path(root) != target_path else set()
        if root_parts & SKIP_DIRS:
            continue
        for file in files:
            if file in SELF_TEST_FILES:
                continue
            fpath = Path(root) / file
            if fpath.resolve() == self_path or fpath.suffix.lower() not in CODE_EXTENSIONS:
                continue
            scanned_files += 1
            text = read_text_auto_encoding(fpath)
            for i, line in enumerate(text.splitlines(), 1):
                if stub_re.search(line):
                    print(f"[ANTI-STUB BLOCKER] {fpath}:{i} -> {line.strip()}")
                    errors += 1
                if vacuous_assert_re.search(line):
                    print(f"[FAKE-ASSERT BLOCKER] {fpath}:{i} -> {line.strip()}")
                    errors += 1
            if has_pass_only_function(text, fpath.suffix.lower()):
                print(f"[ANTI-STUB BLOCKER] {fpath} -> Contains pass-only stub function body!")
                errors += 1

    # C-05 / A4 Fix: If target_dir differs from workspace parent or has 0 files when code is expected
    if scanned_files == 0 and not allow_empty_scan and target_dir != ".":
        print(f"[BLOCKER] Zero code files scanned in target '{target_dir}' (A4 empty-dir evasion blocked)!")
        errors += 1

    errors += verify_g5_g6_g7_ledgers(ws, gate_stage, records)

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
    if cmd in ("--version", "-v"):
        print(VERSION)
        sys.exit(0)

    key_arg = parse_kv_flag(args[1:], "--key=")
    fp_arg = parse_kv_flag(args[1:], "--expect-key-fp=")

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
    elif cmd == "close-bug":
        pos = [a for a in args[1:] if not a.startswith("-")]
        bad_flags = [a for a in args[1:] if a.startswith("-") and not a.startswith("--key=")]
        if bad_flags or len(pos) < 1:
            print("[BLOCKED] Usage: python gate_runner.py close-bug <BUG_ID> [qa_role] [--key=SECRET]")
            sys.exit(1)
        bug_id = pos[0]
        qa_role = pos[1] if len(pos) > 1 else "qa_lead"
        cmd_close_bug(bug_id=bug_id, qa_role=qa_role, key=key_arg)
    elif cmd == "check":
        pos = [a for a in args[1:] if not a.startswith("-")]
        allowed_prefixes = ("--gate=", "--key=", "--expect-key-fp=")
        allowed_exact = {"--require-approval", "--allow-empty-scan"}
        bad_flags = [a for a in args[1:] if a.startswith("-") and a not in allowed_exact and not a.startswith(allowed_prefixes)]
        if bad_flags:
            print(f"[BLOCKED] Invalid flag(s) for check: {bad_flags}")
            sys.exit(1)
        target = pos[0] if pos else "."
        req_apr = "--require-approval" in args[1:]
        allow_empty = "--allow-empty-scan" in args[1:]
        stage = parse_kv_flag(args[1:], "--gate=") or "G4"
        cmd_check(target, require_approval=req_apr, gate_stage=stage, key=key_arg, expected_fp=fp_arg, allow_empty_scan=allow_empty)
    elif cmd == "trust-reset":
        pos = [a for a in args[1:] if not a.startswith("-")]
        bad_flags = [a for a in args[1:] if a.startswith("-") and not a.startswith("--key=")]
        if bad_flags or len(pos) != 1:
            print("[BLOCKED] Usage: python gate_runner.py trust-reset <PROJECT_ID> --key=SECRET")
            sys.exit(1)
        cmd_trust_reset(confirm_token=pos[0], key=key_arg)
    else:
        print("Usage: python gate_runner.py [init | freeze [--force] | approve [role] [--gate=G3..G7] | close-bug <BUG_ID> [qa_role] | check [dir] [--gate=G4|G5|G6|G7] [--expect-key-fp=FP] | trust-reset <PROJECT_ID>] [--key=SECRET]")
