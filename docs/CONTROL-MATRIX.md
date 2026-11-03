# 📊 O9-RD Next V1.6 | Control Implementation Matrix

> **Engineering Principle**: Every governance rule across our **9 Gate Nodes (`G0, G0.5, G1, G2, G3, G4, G5, G6, G7`)** and **4 Routing Tracks (`Trivial, S, M, L`)** is mapped to its exact enforcement layer in V1.6 (`tool-enforced`, `manual-verified`, or `infra-boundary`).

| Gate / ID | Governance Requirement | Status in V1.6 | Enforcement Mechanism & Scope Boundary |
| :--- | :--- | :---: | :--- |
| **G0-01** | Risk-first routing (`Trivial / S / M / L` tracks) | `manual-verified` | Guided by `.cursorrules`, `CLAUDE.md` & Spec checklists; confirmed by Human Owner. |
| **G0.5-01** | Two-way restatement (In-Scope, Out-of-Scope, AC) | `manual-verified` | Enforced via Director System Prompt & IDE rules before coding begins. |
| **G1-01** | Non-Empty Spec & Structured `AC-xxx` Criteria | `tool-enforced` | `gate_runner.py` (v1.6) verifies `spec_and_contracts.md` is non-empty and contains structured `AC-xxx` rows. |
| **G2-01** | Blind 3-Perspective Peer Review (A/B/C) | `manual-verified` | Executed in a fresh stateless LLM session using the G2 Reviewer Prompt. |
| **G3-01** | SHA-256 Baseline & Multi-File `manifest_sha256` | `tool-enforced` | `gate_runner.py freeze` & `approve` compute both `spec_sha256` and composite `manifest_sha256` across all 4 core artifacts & logs. |
| **G3-02** | Detached Approval Record & Label Binding | `tool-enforced` | `gate_runner.py approve` binds role label + baseline hash in `approvals.jsonl` (decoupled from `project_state.json`). |
| **G3-03** | Local Registry & Same-UID Boundary | `infra-boundary` | Local `index.tsv` & `.o9_project_id` prevent accidental resets and support `trust-reset`, while OS-level separation requires CI secret custody or separate UID. |
| **G4-01** | Pattern Scan (Stubs & Trivial Assertions) | `tool-enforced` | `gate_runner.py check` scans code (UTF-8 & UTF-16 BOM, including `tests/` & `.ipynb`, requiring `scanned_files > 0`). |
| **G4-02** | Semantic Reachability & Keyword-Free Stubs | `manual-verified` | Verified via G2/G5 code review & `mock_and_stub_inventory`. |
| **G5-01** | Black-Box-First Physical Source Isolation (E2) | `infra-boundary` | Requires OS/container read-only volume mounts outside single-UID process space. |
| **G5-02** | Repo-Internal Evidence File & Chronological Run | `tool-enforced` | Verifies `evidence_log_ref` is inside repo root, non-empty, and checks the latest (`recorded_at`) run exit code. |
| **G5-03** | Bug Closure Record & Order-Independent Parse | `tool-enforced` | `close-bug` verifies defect exists in YAML first, records `BUG_CLOSE`, and parses YAML items in any key order. |
| **G6-01** | Full RTM Table Verification | `tool-enforced` | Parses markdown table rows (`| AC-xxx |`) without false-firing on prose notes. |
| **G7-01** | Three Decoupled Owner Decisions Check | `tool-enforced` | Verifies Sign-Off (`approved`), Release (`hold|authorized`), and License in `rtm_acceptance.md`. |
