# 📊 O9-RD Next V1.6.4 | Control Implementation Matrix (控制落实矩阵)

> **Engineering Honesty Principle (教材 §14.4 Step 2)**: Never claim a rule is "tool-enforced" if it relies on human review, external container infrastructure, or structural form validation. Every row below maps a governance requirement across our **9 Gate Nodes (`G0, G0.5, G1, G2, G3, G4, G5, G6, G7`)** and **4 Routing Tracks (`Trivial, S, M, L`)** to the exact layer that enforces it in V1.6.4 (`tool-enforced`, `tool-validated (form & consistency)`, `manual-verified`, or `infra-boundary`):
>
> - **`tool-enforced`**: Pure deterministic machine enforcement with cryptographic or hard logical fail-closed blocking that cannot be bypassed via prompt/config edits alone;
> - **`tool-validated (form & consistency)`**: Automated structural and consistency validation (syntax/schema integrity, non-empty, regex patterns, temporal upper/lower bounds, cross-table ledger reconciliation, cryptographic signature binding), while semantic correctness remains bounded by human review or test-case quality;
> - **`manual-verified`**: Requires offline substantive review and sign-off by Human QA / Tech Lead; the tool verifies signature existence and cryptographic integrity;
> - **`infra-boundary`**: Relies on external physical, OS-level, container, or CI boundary isolation (network, read-only volume mounts, separate UID, CI secret custody).
>
> Every `tool-enforced` and `tool-validated` row below is backed by an executable conformance test in [`tests/test_v16_controls.py`](../tests/test_v16_controls.py) or [`tests/test_gate_runner.py`](../tests/test_gate_runner.py). If you change an enforcement mechanism, change its test in the same commit.

---

## 1. Gate-by-Gate Control Matrix

| Gate / Control ID | Governance Requirement | Status in V1.6.4 | Enforcement Mechanism & Scope Boundary |
| :--- | :--- | :---: | :--- |
| **G0-01** | Risk-first routing (`Trivial / S / M / L` tracks) | `manual-verified` | Guided by `.cursorrules`, `CLAUDE.md` & Spec §3 checklists; confirmed by Human Owner. |
| **G0.5-01** | Two-way restatement (In-Scope, Out-of-Scope, AC) | `manual-verified` | Enforced via Director System Prompt & IDE rules before coding begins. |
| **G1-01** | Non-Empty Spec & Structured `AC-xxx` Criteria | `tool-enforced` | `gate_runner.py freeze` calls `verify_spec_structure()`: it refuses an empty `spec_and_contracts.md`, and refuses one with no **markdown table row** carrying an `AC-xxx` id (a prose mention of `AC-001` does not count). |
| **G2-01** | Blind 3-Perspective Peer Review (A/B/C) | `manual-verified` | Executed by spawning a fresh stateless LLM session using the G2 Reviewer Prompt; `review_and_defects.yaml` only records the outcome. |
| **G3-01** | Multi-File Baseline Lock (`spec_sha256` + composite `manifest_sha256`) | `tool-enforced` | `freeze` hashes `spec_and_contracts.md` **plus every file under `o9_workspace/contracts/`**, stores the full `files[]` manifest in the FREEZE record, and signs both `spec_sha256` and the composite `manifest_sha256` into the HMAC payload. `approve` and `check` recompute the manifest and circuit-break on any added, removed or byte-modified baseline file. |
| **G3-02** | Detached Approval Record & Label Binding | `tool-enforced` | `approve` binds the role label + `spec_sha256` + `manifest_sha256` into a detached `approvals.jsonl` record (decoupled from `project_state.json`), and refuses to approve a baseline that mutated after freeze. G7 gate verification requires a dedicated G7 detached approval record (`approve station_master --gate=G7`). |
| **G3-03** | Trust-Root Reset Auditability + Workspace Registry | `tool-enforced` | `~/.o9-trust/index.tsv` is **append-only** and is read on the verification path: if the registry knows a workspace (non-empty `key_fp`) but `anchor_*.sha256` is missing, `init`/`freeze`/`approve`/`close-bug`/`check` all fail closed (`R01`). `trust-reset <PROJECT_ID>` **archives** the old anchor/ledger and immediately writes a signed, hash-chained record `#1 {type: TRUST_RESET, archived_ledger_sha256, previous_key_fp, new_key_fp}`, so a reset can never again be byte-indistinguishable from a brand-new project (`T2`). `check` refuses **both** an extra unexplained `approvals.jsonl.bak.*` file **and** a `TRUST_RESET` whose named archive has been deleted — Same-UID agent deleting anchor + index.tsv + ledger simultaneously is an OS-level privilege boundary (infra-boundary). |
| **G3-04** | Same-UID Key Custody | `infra-boundary` | Preventing a same-UID agent from reading `O9_APPROVAL_SECRET` requires CI secret custody, a separate OS user, or an external container. No local Python process can enforce this — see §2. |
| **G4-01** | Anti-Stubbing & Vacuous Assert Scan | `tool-validated (form & consistency)` | `check` scans code (UTF-8 & UTF-16 BOM, including `tests/`, `.ipynb`, `.mjs`, `.cjs`, `.pyi`, and full-tree code without directory exclusions except `.git`, `o9_workspace`, `node_modules`, `.venv`, `__pycache__`) for case-insensitive `TODO/FIXME/XXX/HACK`, `raise NotImplementedError`, `assert True`, `assert(True)`, `assert <truthy-constant>`, `assert x == x`, `assertTrue(1 == 1)`, `assertEqual(1, 1)`, `assertEqual(len([]), len([]))`, docstring-aware `pass`/`...`-only bodies (including `def f(): pass` and `pass # comment`). Target path must be confined to repository root. Zero-file scan is blocked for all target spellings unless `--allow-empty-scan`. Conformance tests exempt only with `# O9-RD-OFFICIAL-CONFORMANCE-TEST` marker and verified official SHA-256. |
| **G4-02** | Semantic Reachability & Keyword-Free Stubs | `manual-verified` | Regex cannot build AST call-graphs; production mock-leak verification relies on G2/G5 code review & `mock_and_stub_inventory`. |
| **G5-01** | Black-Box-First Physical Source Isolation (E2) | `infra-boundary` | Requires OS/container read-only volume mounts (e.g. Docker `:ro` or an external sandbox) outside single-UID process space; the tool verifies `source_code_hidden_verified: true` in structured `g5_test_runs` items. Factory template initializes with `source_code_hidden_verified: false` and `exit_code: -1` (default red). |
| **G5-02** | Repo-Internal Evidence & Chronological Run Selection | `tool-validated (form & consistency)` | Every `evidence_log_ref` must resolve **inside the repository root** (absolute paths and `..` escapes are blocked) and be a non-empty regular file; `/dev/null`-style sinks are rejected. Evaluates pure structured dict items from `g5_test_runs` (quote-aware comment stripping, no regex extraction). **`recorded_at` is strictly bounded**: must be $\ge$ baseline freeze timestamp (no stale/back-dated runs) and $\le \text{UTC now} + 5\text{s}$ (no future runs). Latest run selected chronologically must report `exit_code: 0`. |
| **G5-03** | Bug Closure Record, Pure Dict Parse & Signed Review State | `tool-validated (form & consistency)` | `close-bug` requires defect to exist in YAML and folds `review_yaml_sha256` into HMAC payload. Parsing strips comments with quote-awareness, rejects Flow-style `{}` and duplicate keys. G5/G6/G7 checks verify that the latest `BUG_CLOSE`'s `review_yaml_sha256` matches current YAML (blocks post-sign tampering). |
| **G6-01** | Full RTM Table Verification & QA Run Reconciliation | `tool-validated (form & consistency)` | Parses markdown table rows (`\| AC-xxx \|`) only; requires **100% coverage of all frozen `AC-xxx` IDs from `spec_and_contracts.md`**; blocks `not-run\|failed\|blocked\|not-covered\|skipped\|pending` rows. Cross-validates all referenced `RUN-[A-Za-z0-9_-]+` against passing runs (`exit_code == 0`) in `g5_test_runs`. Requires every AC row to reference at least one valid passing RUN-xxx ID (N3b fixed). Factory template initializes with `not-covered` and `not-run` (default red). |
| **G7-01** | Three Decoupled Owner Decisions Check | `tool-validated (form & consistency)` | Verifies explicit Sign-Off (`approved`), Release (`hold` or `authorized`), and Ownership & License in `rtm_acceptance.md`. |
| **OBS-01** | Observability of the Unsigned Artifacts | `tool-enforced` | Every `check` prints the current `sha256` of `review_and_defects.yaml` and `rtm_acceptance.md` in its `[OK]`/`[INFO]` output, so a human can diff them against git history. This is *observability*, not tamper-evidence — see the disclosure table in §2. |

---

## 2. Threat Model & OS/Container Boundary Disclosure

`gate_runner.py` is a **zero-dependency, single-file Verifiable Minimal Control Plane**. It defends against *accidental drift* and *naive reward-hacking* (deleted assertions, `TODO` stubs, phantom bug closures, post-freeze spec edits, back-dated QA evidence), and it makes tampering detectable through an HMAC hash-chained ledger plus an external trust anchor.

**Architectural Boundary (Same-UID Limitation)**:

If an autonomous coding agent is granted unrestricted shell access under the **exact same OS user account (UID)** and environment where `O9_APPROVAL_SECRET` is stored in plaintext, that agent shares the human's privilege domain. It can therefore read the signing secret, and any signature it produces is indistinguishable from a human one at the process level.

Consequently, for **L-Track (high-risk) isolation**, the signing secret and the `gate_runner.py check` verification must be held/executed in an **independent CI runner (e.g. GitHub Actions with protected secrets)**, a separate OS user, or an external container host outside the agent's sandbox.

`trust-reset` is gated on the signing secret and a project-id spelling check. A same-UID agent holding the secret **can** invoke it; it is therefore an *auditable* recovery path, not a security boundary against such an agent. What V1.6.4 guarantees is that such a reset cannot happen **silently**: it archives the previous anchor and ledger, and it writes a signed `TRUST_RESET` record as record #1 of the new chain.

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
| **Unreported defects (`defects: []`)** | `review_yaml_sha256` is cryptographically bound when `close-bug` signs a `BUG_CLOSE` record. If an agent declares `defects: []`, no `BUG_CLOSE` signature is required — the tool cannot force an agent to report a defect it wishes to hide. |

---

## 3. v1.6.4 Change Summary

| Area | v1.6.3 behaviour | v1.6.4 behaviour |
| :--- | :--- | :--- |
| G5-02 / P13 | Sub-second freeze timestamp vs second-precision `recorded_at` caused same-second false positive | Clears microsecond on freeze timestamp (`freeze_floor = freeze_dt.replace(microsecond=0)`) |
| G4-01 / P8 | `raise NotImplementedError` regex blocked standard `@abstractmethod` ABC classes | Removed from vacuous assert scan (handled by AST/manual review G4-02) |
| G6-01 / N3b | AC row without any `RUN-xxx` could pass if no failure keyword present | Requires every AC row to reference at least one `RUN-xxx` ID (unless `no-run-required manual`) |
| Threat Model / N4 | Implicit disclosure on `defects: []` | Explicit disclosure added: tool cannot compel an agent to report a defect if it claims `defects: []` |
| Dead Code | `ROOT_ONLY_SKIP_DIRS = set()` | Cleaned up unused constant |

## 4. v1.6.3 Change Summary

| Area | v1.6.2 behaviour | v1.6.3 behaviour |
| :--- | :--- | :--- |
| Tier System | 3-tier classification | 4-tier classification: introduced `tool-validated (form & consistency)` |
| G4-01 / 1.11b | Skipped `docs/`, `templates/`, `prompts/` at root | Full-tree scanning without directory exclusions (catches stubs in `docs/prod.py`) |
| G4-01 / 1.12 | `.py`, `.ts` etc. | Added `.mjs`, `.cjs`, `.pyi`, `raise NotImplementedError`, `assertTrue(1==1)`, `assertEqual(len([]), len([]))`, docstring-aware pass body |
| G4-01 / 1.13 | Exempted self-tests by path name | Requires `# O9-RD-OFFICIAL-CONFORMANCE-TEST` line 1 marker and official SHA-256 match |
| G5-02 / Top 2 | Regex scanning over entire YAML | Pure structured dict extraction from `g5_test_runs`; quote-aware comment stripping |
| G5-02 / N5, N6 | Timestamp drift +300s, no lower bound | Upper bound tightened to +5s; lower bound enforced ($\ge \text{latest freeze timestamp}$) |
| G6-01 / N3 | RTM rows checked independently | Cross-checks referenced `RUN-xxx` against `g5_test_runs` with `exit_code == 0` |
| Lock / 1.14b | Stale lock cleanup could fail on readonly file | Unlinks lock path safely with `set_writable` |
| Robustness / 1.16 | Crash/traceback if ledger/state replaced by directory | Fail-closed blocker print without unhandled Python traceback |
