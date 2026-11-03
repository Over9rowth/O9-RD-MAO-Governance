# 📊 O9-RD Next V1.6 | Control Implementation Matrix (控制落实矩阵)

> **Engineering Honesty Principle (教材 §14.4 Step 2)**: Never claim a rule is "tool-enforced" if it relies on human review or external container infrastructure. Every row below maps a governance requirement across our **9 Gate Nodes (`G0, G0.5, G1, G2, G3, G4, G5, G6, G7`)** and **4 Routing Tracks (`Trivial, S, M, L`)** to the exact layer that enforces it in V1.6 (`tool-enforced`, `manual-verified`, or `infra-boundary`).
>
> Every `tool-enforced` row in this document is backed by an executable conformance test in [`tests/test_v16_controls.py`](../tests/test_v16_controls.py), so this matrix cannot drift away from the implementation.

---

## 1. Gate-by-Gate Control Matrix

| Gate / Control ID | Governance Requirement | Status in V1.6 | Enforcement Mechanism & Scope Boundary |
| :--- | :--- | :---: | :--- |
| **G0-01** | Risk-first routing (`Trivial / S / M / L` tracks) | `manual-verified` | Guided by `.cursorrules`, `CLAUDE.md` & Spec §3 checklists; confirmed by Human Owner. |
| **G0.5-01** | Two-way restatement (In-Scope, Out-of-Scope, AC) | `manual-verified` | Enforced via Director System Prompt & IDE rules before coding begins. |
| **G1-01** | Non-Empty Spec & Structured `AC-xxx` Criteria | `tool-enforced` | `gate_runner.py freeze` calls `verify_spec_structure()`: it refuses an empty `spec_and_contracts.md`, and refuses one with no **markdown table row** carrying an `AC-xxx` id (a prose mention of `AC-001` does not count). |
| **G2-01** | Blind 3-Perspective Peer Review (A/B/C) | `manual-verified` | Executed by spawning a fresh stateless LLM session using the G2 Reviewer Prompt; `review_and_defects.yaml` only records the outcome. |
| **G3-01** | Multi-File Baseline Lock (`spec_sha256` + composite `manifest_sha256`) | `tool-enforced` | `freeze` hashes `spec_and_contracts.md` **plus every file under `o9_workspace/contracts/`**, stores the full `files[]` manifest in the FREEZE record, and signs both `spec_sha256` and the composite `manifest_sha256` into the HMAC payload. `approve` and `check` recompute the manifest and circuit-break on any added, removed or byte-modified baseline file. |
| **G3-02** | Detached Approval Record & Label Binding | `tool-enforced` | `approve` binds the role label + `spec_sha256` + `manifest_sha256` into a detached `approvals.jsonl` record (decoupled from `project_state.json`), and refuses to approve a baseline that mutated after freeze. |
| **G3-03** | Local Workspace Registry & Same-UID Boundary | `infra-boundary` | **Tool-supported half**: `.o9_project_id` pins the workspace↔project binding and the local registry `~/.o9-trust/index.tsv` refuses accidental re-binding, while the new `trust-reset <PROJECT_ID>` subcommand is the sanctioned, secret-gated escape hatch that *archives* the old anchor/ledger instead of bricking the project — and because the project id can be recovered from `index.tsv`, it still works after `o9_workspace/` has been deleted entirely. **Infra half**: preventing a same-UID agent from reading `O9_APPROVAL_SECRET` requires CI secret custody, a separate OS user, or an external container — the Python tool cannot enforce that. |
| **G4-01** | Anti-Stubbing & Vacuous Assert Scan | `tool-enforced` | `check` scans code (UTF-8 & UTF-16 BOM, including `tests/` & `.ipynb`) for case-insensitive `TODO/FIXME/XXX/HACK`, `assert True`, `assert x == x`, and `pass`-only function bodies, and blocks a zero-file scan (`scanned_files > 0`). |
| **G4-02** | Semantic Reachability & Keyword-Free Stubs | `manual-verified` | Regex cannot build AST call-graphs; production mock-leak verification relies on G2/G5 code review & `mock_and_stub_inventory`. |
| **G5-01** | Black-Box-First Physical Source Isolation (E2) | `infra-boundary` | Requires OS/container read-only volume mounts (e.g. Docker `:ro` or an external sandbox) outside single-UID process space; the tool only verifies the `source_code_hidden_verified: true` attestation. |
| **G5-02** | Repo-Internal Evidence & Chronological Run Selection | `tool-enforced` | Every `evidence_log_ref` must resolve **inside the repository root** (absolute paths and `..` escapes are blocked) and be a non-empty file; `/dev/null`-style sinks are rejected. The latest QA run is selected by `recorded_at` chronology (`select_latest_g5_run`), so back-filling an older passing run cannot mask a newer failing one. |
| **G5-03** | Bug Closure Record & Order-Independent Parse | `tool-enforced` | `close-bug` requires the defect to already exist in `review_and_defects.yaml` (blocks phantom pre-signing), records a signed `BUG_CLOSE` entry, and the YAML parser (`extract_yaml_items`) is indentation-based so keys may appear in **any order** and under **any parent key** (`defects:`, `open_defects:` …). |
| **G6-01** | Full RTM Table Verification | `tool-enforced` | Parses markdown table rows (`\| AC-xxx \|`) only, so prose notes mentioning a previously failed build do not false-fire; blocks `not-run` / `failed` / `blocked` / `not-covered` rows. |
| **G7-01** | Three Decoupled Owner Decisions Check | `tool-enforced` | Verifies explicit Sign-Off (`approved`), Release (`hold` or `authorized`), and Ownership & License in `rtm_acceptance.md`. |

---

## 2. Threat Model & OS/Container Boundary Disclosure

`gate_runner.py` is a **zero-dependency, single-file Verifiable Minimal Control Plane**. It defends against *accidental drift* and *naive reward-hacking* (deleted assertions, `TODO` stubs, phantom bug closures, post-freeze spec edits, back-dated QA evidence), and it makes tampering detectable through an HMAC hash-chained ledger plus an external trust anchor.

**Architectural Boundary (Same-UID Limitation)**:

If an autonomous coding agent is granted unrestricted shell access under the **exact same OS user account (UID)** and environment where `O9_APPROVAL_SECRET` is stored in plaintext, that agent shares the human's privilege domain. It can therefore read the signing secret, and any signature it produces is indistinguishable from a human one at the process level.

Consequently, for **L-Track (high-risk) isolation**, the signing secret and the `gate_runner.py check` verification must be held/executed in an **independent CI runner (e.g. GitHub Actions with protected secrets)**, a separate OS user, or an external container host outside the agent's sandbox. The `trust-reset` escape hatch is likewise gated on the human-held secret and an explicit project-id confirmation token — it is a human recovery path, not an agent-reachable bypass.

### What the tool does NOT enforce

| Claim | Reality |
| :--- | :--- |
| Physical source-code hiding during G5 | Needs container/volume isolation. The tool only verifies the `source_code_hidden_verified` attestation in YAML. |
| Semantic dead-code / mock reachability | Undecidable with regex; assigned to human/LLM review (G4-02 `manual-verified`). |
| Secret custody against a same-UID agent | Out of scope for a local Python process; requires CI or a separate UID. |
| Whether a human actually said "approved" | The tool proves *someone holding the key* approved. Binding that key to a human is an organizational control. |

---

## 3. v1.6 Change Summary

| Area | v1.5 behaviour | v1.6 behaviour |
| :--- | :--- | :--- |
| G1-01 | Only checked that the spec file existed | Blocks empty specs and specs without structured `AC-xxx` table rows |
| G3-01 | Single-file `spec_sha256` | Composite `manifest_sha256` across spec + `o9_workspace/contracts/**`, signed and re-verified at approve/check |
| G3-02 | Bound spec hash only | Binds `spec_sha256` **and** `manifest_sha256` |
| G3-03 | Permanent lockout after a wiped ledger (no `trust-reset`) | `.o9_project_id` + `index.tsv` registry + `trust-reset` recovery path (also recovers a fully deleted `o9_workspace/`) |
| G5-02 | Checked `exit_code` in document order; absolute evidence paths allowed | Latest run chosen by `recorded_at`; evidence confined to the repo root |
| G5-03 | Item parsing assumed `bug_id` came first | Order-independent, indentation-aware item parsing |
