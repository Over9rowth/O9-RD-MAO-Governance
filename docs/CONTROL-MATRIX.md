# 📊 O9-RD Next V1.5 | Control Implementation Matrix (控制落实矩阵)

> **Engineering Honesty Principle (教材 §14.4 Step 2)**: Never claim a rule is "tool-enforced" if it relies on human review or external container infrastructure. This matrix explicitly maps every O9-RD governance requirement across our **9 Gate Nodes (`G0, G0.5, G1, G2, G3, G4, G5, G6, G7`)** and **4 Routing Tracks (`Trivial, S, M, L`)** to its exact enforcement layer in V1.5.

---

## 1. Gate-by-Gate Control Matrix

| Gate / Control ID | Governance Requirement | Status in V1.5 | Enforcement Mechanism & Scope Boundary |
| :--- | :--- | :---: | :--- |
| **G0-01** | Risk-first routing (`Trivial / S / M / L` tracks) | `manual-verified` | Guided by `.cursorrules`, `CLAUDE.md` & Spec §3 checklists; confirmed by Human Owner. |
| **G0.5-01** | Two-way restatement (In-Scope, Out-of-Scope, AC) | `manual-verified` | Enforced via Director System Prompt & IDE rules before coding begins. |
| **G1-01** | Three-Tier Contracts (`spec_and_contracts.md`) | `tool-enforced` | `gate_runner.py` verifies presence and non-empty structure of spec & test harness. |
| **G2-01** | Blind 3-Perspective Peer Review (A/B/C) | `manual-verified` | Executed by spawning a fresh stateless LLM session using the G2 Reviewer Prompt. |
| **G3-01** | SHA-256 Baseline Freeze & Monotonic Sequence | `tool-enforced` | `gate_runner.py freeze` computes SHA-256, assigns monotonic `seq`, and signs via HMAC-SHA256 in `approvals.jsonl`. |
| **G3-02** | Detached Approval Record Binding | `tool-enforced` | `gate_runner.py approve` binds role label + baseline hash in `approvals.jsonl` (decoupled from `project_state.json`). |
| **G3-03** | External Trust Anchor & Anti-Reset Protection | `tool-enforced` | `sync_external_anchor` pins ledger hash, `seq`, and `key_fp` in `~/.o9-trust/`. `init` is blocked from deleting existing anchors (C-01/C-02 fixed). |
| **G4-01** | Anti-Stubbing & Vacuous Assert Scan | `tool-enforced` | `gate_runner.py check` scans code (UTF-8 & UTF-16 BOM, including `tests/` & `.ipynb`) for case-insensitive `TODO/FIXME`, `assert True`, `assert x==x`, and `pass`-only functions. |
| **G4-02** | Semantic Mock-Reachability Analysis | `manual-verified` | Regex cannot build AST call-graphs; production mock-leak verification relies on G2/G5 code review & `mock_and_stub_inventory`. |
| **G5-01** | Black-Box-First Physical Source Isolation (E2) | `infra-boundary` | Requires OS/container read-only volume mounts (e.g., Docker `:ro` or E2B sandbox) outside single-UID process space. |
| **G5-02** | Real Non-Empty Evidence Log & Latest `exit_code` | `tool-enforced` | `gate_runner.py check --gate=G5` verifies `evidence_log_ref` is a real non-empty file and checks the latest run's `exit_code == 0`. |
| **G5-03** | Cryptographic Bug Closure Binding & Pre-Sign Block | `tool-enforced` | `gate_runner.py close-bug` requires defect to exist in YAML first (A18 fixed), records HMAC `BUG_CLOSE`, and blocks `open`/`rejected`/unsigned closures. |
| **G6-01** | Full RTM Table Verification | `tool-enforced` | `gate_runner.py check --gate=G6` parses markdown table rows (`| AC-xxx |`) and blocks `not-run`/`failed`/`blocked` items without false-firing on prose notes. |
| **G7-01** | Three Decoupled Owner Decisions Check | `tool-enforced` | `gate_runner.py check --gate=G7` verifies explicit Sign-Off (`approved`), Release (`hold|authorized`), and License in `rtm_acceptance.md`. |

---

## 2. Threat Model & OS/Container Boundary Disclosure

`gate_runner.py` is a **zero-dependency, single-file Verifiable Minimal Control Plane** designed to catch accidental drift, naive reward-hacking (`TODO` stubs, fake assertions, unclosed bugs), and unauthorized spec edits.

**Architectural Boundary (Same-UID Limitation)**:
If an autonomous coding agent is granted unrestricted shell access under the **exact same OS user account (UID)** and environment where `O9_APPROVAL_SECRET` is stored in plaintext, the agent shares the human's privilege domain. For **L-Track high-risk isolation**, the secret and `gate_runner.py check` verification must be executed in an **independent CI runner (e.g., GitHub Actions with protected secrets)** or an external container host outside the agent's sandbox.
