# 📊 O9-RD Next V1.6.2 | Control Implementation Matrix (控制落实矩阵)

> **Engineering Honesty Principle (教材 §14.4 Step 2)**: Never claim a rule is "tool-enforced" if it relies on human review or external container infrastructure. Every row below maps a governance requirement across our **9 Gate Nodes (`G0, G0.5, G1, G2, G3, G4, G5, G6, G7`)** and **4 Routing Tracks (`Trivial, S, M, L`)** to the exact layer that enforces it in V1.6.2 (`tool-enforced`, `manual-verified`, or `infra-boundary`).
>
> Every `tool-enforced` row below is backed by an executable conformance test in [`tests/test_v16_controls.py`](../tests/test_v16_controls.py) or [`tests/test_gate_runner.py`](../tests/test_gate_runner.py) — **including G4-01, which was the one row without a test in V1.6 and was consequently the one row that had drifted.** If you change an enforcement mechanism, change its test in the same commit.

---

## 1. Gate-by-Gate Control Matrix

| Gate / Control ID | Governance Requirement | Status in V1.6.2 | Enforcement Mechanism & Scope Boundary |
| :--- | :--- | :---: | :--- |
| **G0-01** | Risk-first routing (`Trivial / S / M / L` tracks) | `manual-verified` | Guided by `.cursorrules`, `CLAUDE.md` & Spec §3 checklists; confirmed by Human Owner. |
| **G0.5-01** | Two-way restatement (In-Scope, Out-of-Scope, AC) | `manual-verified` | Enforced via Director System Prompt & IDE rules before coding begins. |
| **G1-01** | Non-Empty Spec & Structured `AC-xxx` Criteria | `tool-enforced` | `gate_runner.py freeze` calls `verify_spec_structure()`: it refuses an empty `spec_and_contracts.md`, and refuses one with no **markdown table row** carrying an `AC-xxx` id (a prose mention of `AC-001` does not count). |
| **G2-01** | Blind 3-Perspective Peer Review (A/B/C) | `manual-verified` | Executed by spawning a fresh stateless LLM session using the G2 Reviewer Prompt; `review_and_defects.yaml` only records the outcome. |
| **G3-01** | Multi-File Baseline Lock (`spec_sha256` + composite `manifest_sha256`) | `tool-enforced` | `freeze` hashes `spec_and_contracts.md` **plus every file under `o9_workspace/contracts/`**, stores the full `files[]` manifest in the FREEZE record, and signs both `spec_sha256` and the composite `manifest_sha256` into the HMAC payload. `approve` and `check` recompute the manifest and circuit-break on any added, removed or byte-modified baseline file. |
| **G3-02** | Detached Approval Record & Label Binding | `tool-enforced` | `approve` binds the role label + `spec_sha256` + `manifest_sha256` into a detached `approvals.jsonl` record (decoupled from `project_state.json`), and refuses to approve a baseline that mutated after freeze. G7 gate verification requires a dedicated G7 detached approval record (`approve station_master --gate=G7`). |
| **G3-03** | Trust-Root Reset Auditability + Workspace Registry | `tool-enforced` | `~/.o9-trust/index.tsv` is **append-only** and is now **read on the verification path**: if the registry knows a workspace (non-empty `key_fp`) but `anchor_*.sha256` is missing, `init`/`freeze`/`approve`/`close-bug`/`check` all fail closed (`R01`). `trust-reset <PROJECT_ID>` **archives** the old anchor/ledger and immediately writes a signed, hash-chained record `#1 {type: TRUST_RESET, archived_ledger_sha256, previous_key_fp, new_key_fp}`, so a reset can never again be byte-indistinguishable from a brand-new project (`T2`). `check` refuses **both** an extra unexplained `approvals.jsonl.bak.*` file **and** a `TRUST_RESET` whose named archive has been deleted — Same-UID agent deleting anchor + index.tsv + ledger simultaneously is an OS-level privilege boundary (infra-boundary). |
| **G3-04** | Same-UID Key Custody | `infra-boundary` | Preventing a same-UID agent from reading `O9_APPROVAL_SECRET` requires CI secret custody, a separate OS user, or an external container. No local Python process can enforce this — see §2. |
| **G4-01** | Anti-Stubbing & Vacuous Assert Scan | `tool-enforced` | `check` scans code (UTF-8 & UTF-16 BOM, including `tests/` & `.ipynb`) for case-insensitive `TODO/FIXME/XXX/HACK`, `assert True`, `assert(True)`, `assert <truthy-constant>`, `assert x == x`, `assertEqual(1, 1)`, `pass`/`...`-only bodies (including `def f(): pass` and `pass  # comment`). Target path must be confined to repository root; `SKIP_DIRS` (`docs`, `templates`, `prompts`) are skipped only at top-level root (`len(rel_parts) == 1`), while subdirectories like `src/docs/` are scanned. Zero-file scan is blocked for all target spellings unless `--allow-empty-scan`. Conformance tests exempt only at absolute path. |
| **G4-02** | Semantic Reachability & Keyword-Free Stubs | `manual-verified` | Regex cannot build AST call-graphs; production mock-leak verification relies on G2/G5 code review & `mock_and_stub_inventory`. |
| **G5-01** | Black-Box-First Physical Source Isolation (E2) | `infra-boundary` | Requires OS/container read-only volume mounts (e.g. Docker `:ro` or an external sandbox) outside single-UID process space; the tool strips comments before verifying the `source_code_hidden_verified: true` attestation in `review_and_defects.yaml`. Factory template initializes with `source_code_hidden_verified: false` and `exit_code: -1` (default red). |
| **G5-02** | Repo-Internal Evidence & Chronological Run Selection | `tool-enforced` | Every `evidence_log_ref` must resolve **inside the repository root** (absolute paths and `..` escapes are blocked) and be a non-empty file (no dummy log auto-created at `init`); `/dev/null`-style sinks are rejected. **`recorded_at` is mandatory** for every `g5_test_runs` item (unstamped runs rejected; future timestamps >300s clock drift blocked), ensuring latest run is chosen chronologically without document-order fallback. |
| **G5-03** | Bug Closure Record, Order-Independent Parse & Signed Review State | `tool-enforced` | `close-bug` requires defect to exist in YAML and folds `review_yaml_sha256` into HMAC payload. Parsing strips comments, rejects Flow-style `{}` and duplicate keys. G5/G6/G7 checks verify that the latest `BUG_CLOSE`'s `review_yaml_sha256` matches current YAML (blocks post-sign tampering). |
| **G6-01** | Full RTM Table Verification | `tool-enforced` | Parses markdown table rows (`\| AC-xxx \|`) only; requires **100% coverage of all frozen `AC-xxx` IDs from `spec_and_contracts.md`**; blocks `not-run\|failed\|blocked\|not-covered\|skipped\|pending` rows. Factory template initializes with `not-covered` and `not-run` (default red). |
| **G7-01** | Three Decoupled Owner Decisions Check | `tool-enforced` | Verifies explicit Sign-Off (`approved`), Release (`hold` or `authorized`), and Ownership & License in `rtm_acceptance.md`. |
| **OBS-01** | Observability of the Unsigned Artifacts | `tool-enforced` | Every `check` prints the current `sha256` of `review_and_defects.yaml` and `rtm_acceptance.md` in its `[OK]`/`[INFO]` output, so a human can diff them against git history. This is *observability*, not tamper-evidence — see the disclosure table in §2. |

---

## 2. Threat Model & OS/Container Boundary Disclosure

`gate_runner.py` is a **zero-dependency, single-file Verifiable Minimal Control Plane**. It defends against *accidental drift* and *naive reward-hacking* (deleted assertions, `TODO` stubs, phantom bug closures, post-freeze spec edits, back-dated QA evidence), and it makes tampering detectable through an HMAC hash-chained ledger plus an external trust anchor.

**Architectural Boundary (Same-UID Limitation)**:

If an autonomous coding agent is granted unrestricted shell access under the **exact same OS user account (UID)** and environment where `O9_APPROVAL_SECRET` is stored in plaintext, that agent shares the human's privilege domain. It can therefore read the signing secret, and any signature it produces is indistinguishable from a human one at the process level.

Consequently, for **L-Track (high-risk) isolation**, the signing secret and the `gate_runner.py check` verification must be held/executed in an **independent CI runner (e.g. GitHub Actions with protected secrets)**, a separate OS user, or an external container host outside the agent's sandbox.

`trust-reset` is gated on the signing secret and a project-id spelling check. A same-UID agent holding the secret **can** invoke it; it is therefore an *auditable* recovery path, not a security boundary against such an agent. What V1.6.2 guarantees is that such a reset cannot happen **silently**: it archives the previous anchor and ledger, and it writes a signed `TRUST_RESET` record as record #1 of the new chain.

### What the tool does NOT enforce

| Claim | Reality |
| :--- | :--- |
| Physical source-code hiding during G5 | Needs container/volume isolation. The tool only verifies the `source_code_hidden_verified` attestation in YAML. |
| Semantic dead-code / mock reachability | Undecidable with regex; assigned to human/LLM review (G4-02 `manual-verified`). |
| Secret custody against a same-UID agent | Out of scope for a local Python process; requires CI or a separate UID. |
| Whether a human actually said "approved" | The tool proves *someone holding the key* approved. Binding that key to a human is an organizational control. |
| **Tamper-evidence for the G5/G6/G7 artifacts** | `review_and_defects.yaml` and `rtm_acceptance.md` sit **outside** the signed `manifest_sha256`, because they legitimately mutate during a run (defects are added, runs are appended). Their integrity must come from **git history / the audit ledger / `review_yaml_sha256` on each `BUG_CLOSE`**, not from `freeze`. `check` prints their current SHA-256 so a human can compare. |
| **Anti-rollback of the whole signed history** | There is a monotonic `seq` and an anchored minimum length, but an attacker who can restore *every* artifact (ledger + anchor + index + state) to an older consistent snapshot is indistinguishable from a project that simply stopped. True anti-rollback needs an external monotonic witness (git tag on a protected branch, transparency log, TSA). |
| **Who actually ran the tests** | The tool proves a non-empty evidence file exists and that a `recorded_at`-ordered run reports `exit_code: 0`. Proving *a real test process produced that file* needs signed CI artifacts. |

---

## 3. v1.6.1 Change Summary

| Area | v1.6 behaviour | v1.6.1 behaviour |
| :--- | :--- | :--- |
| G4-01 | `check .` exempt from the zero-file guard (claim was false) | Guard applies to every spelling of the target; `--allow-empty-scan` prints `[WARNING]` |
| G4-01 / R04 | Files exempt by **bare filename** (`confirm.py`, `redteam.py` …) | Exempt only at the absolute path of this tool's own conformance tests; a project's `tests/` stays scanned |
| G3-03 / R01 | `init`/`check` blind to the registry; deleting the anchor looked like a fresh project | Registry is append-only **and** read on the verification path; a missing anchor over a known workspace fails closed |
| G3-03 / T2 | `trust-reset` left an empty ledger — indistinguishable from a new project | `TRUST_RESET` signed record #1 (`archived_ledger_sha256`, `previous_key_fp`, `new_key_fp`); an unexplained `approvals.jsonl.bak.*` is refused |
| G5-02 / R09c | `recorded_at` optional, fell back to document order | `recorded_at` mandatory; unstamped runs are inadmissible |
| R10 | Lock directory inside the audited workspace, 10 s wait, no reclaim | Lock under `~/.o9-trust/locks/`, `pid:timestamp` owner file, 2 s wait, stale lock (>4 s or dead owner) reclaimed with a warning |
| G5-03 | `BUG_CLOSE` bound only to bug id + role + baseline | Also binds `review_yaml_sha256` (the review ledger as it was at signing time) |
| G4-01 / R08 | `pass`-only and `assert x == x` only | Adds `assert(True)`, truthy-constant asserts, `assertEqual(1, 1)`, single-line `def f(): pass`, and `pass  # comment` |
| OBS-01 | Unsigned artifacts invisible | `check` prints both artifacts' SHA-256 for human diffing |
