# 🛠️ O9-RD Next V1.6.4 | Master Workflow Specification & 4-Artifact Templates (English Edition)

> **Positioning**: Production-ready Multi-Agent Orchestration (MAO) governance standard.  
> **Core Principle**: Separate the **Deterministic Control Plane** (Python/Shell scripts, Git, container mounts, SHA-256 verification) from the **Non-Deterministic Execution Plane** (LLM agents).

---

# Part 1: The 10 Non-Negotiable Commandments

1. **Single Source of Truth (SSOT)**: Only one valid baseline exists at any time. Agents never pass requirements via chat history; all handoffs occur through versioned files. Internal baseline conflicts immediately `block` affected work.
2. **Code-Enforced Control Plane**: Calculating SHA-256 hashes, packaging read-only review bundles, enforcing path whitelists, and scanning for `TODO`/Mock leaks must be performed by deterministic scripts (`gate_runner`), never by an LLM.
3. **G0.5 Two-Way Confirmation**: Before designing or coding, the Director Agent must restate *In-Scope*, *Out-of-Scope*, and *Acceptance Criteria (AC)* in plain language and obtain explicit human confirmation.
4. **Three-Tier Contracts First (G1)**: Deliver machine-verifiable **Data/Interface Schemas**, **Behavior/Invariants**, and a **Testability Contract (`test-harness`)** before coding.
5. **Separation of Duties (SoD)**: Any agent/session that designs or writes code for a change is strictly disqualified from acting as its G2 Reviewer, G5 Tester, or G6 Auditor.
6. **G2 Blind Review & Three Perspectives**: Reviewers run in fresh, stateless sessions with read-only whitelisted bundles (mutually blind before initial submission). Every reviewer must evaluate **Perspective A (Architecture & Requirements Fit)**, **Perspective B (Security & Reliability)**, and **Perspective C (Simpler Alternatives)**.
7. **G3 Detached Cryptographic Signature**: Freeze candidate files, compute their byte-level SHA-256 `manifest_sha256`, and bind human approval in an external JSON record referencing that hash. Never write approval status back into hashed files.
8. **G5 Black-Box First Iron Law**: Independent QA agents must first design and execute black-box tests **without read access to implementation source code (`src/`)**. Only after first-round black-box evidence is locked may they read source code for white-box inspection and mandatory L-track Fuzzing. Developers cannot close bugs.
9. **G7 Decoupled Sign-Off & Release**: Technical acceptance (G6), human sign-off, and production release authorization are recorded separately.
10. **Honest Evidence & Manual Todo**: Silence or timeout is never approval. Scenarios unreachable by AI (physical hardware, real mobile UX) must remain `not-run` or `blocked` and generate a *Manual Verification Todo Card*—never hallucinate `passed`.

---

# Part 2: Risk Routing (Trivial / S / M / L) & Isolation Levels (E0 - E2)

## 2.1 Veto-Based Risk Routing (Evaluated Top-Down)
*   🔴 **L-Track (High-Risk / Strict Governance)** — Triggered immediately if ANY of the following apply:
    1. Changes to authentication, authorization, tenant isolation, or key management.
    2. New/expanded collection or export of sensitive PII, credentials, or confidential data.
    3. Irreversible deletion/migration or broad production database mutations.
    4. Billing, payment flows, financial transactions, or high material loss risk.
    5. Broad production infrastructure or critical security config changes.
    6. Granting Agents new external side-effect tool authorities.
    7. Cross-system core architecture overhaul.
*   🟡 **M-Track (Standard Agile)** — No L-track triggers, but involves new business behavior, cross-module interfaces, or schema changes. (Requires $\ge 1$ G2 blind reviewer + Black-box/White-box QA + full RTM).
*   🟢 **S-Track (Lightweight Fast-Track)** — Local copy/style/isolated fix + no AC/interface/permission changes + instant rollback + independent black-box verifier assigned.Exempts G2 review and targets **2 Human Touchpoints** (Touchpoint 1: Confirm G0.5 + G3 baseline; Touchpoint 2: Verify G5 evidence + G7 sign-off).
*   ⚪ **Trivial Track** — Pure comments/README typos (< 20 lines, zero logic/config impact). Director shows `git diff` -> Human approves -> Merge.

## 2.2 Sandbox Isolation Evidence Levels
*   **E0 (Unverified)**: Prompt instructions only ("please don't read `src/`"). Does NOT count toward independent review/QA minimums.
*   **E1 (Controlled Session)**: Fresh API session + explicit static input pack + no chat history inheritance. Allowed for S/M tracks.
*   **E2 (Technical Sandbox Isolation — Mandatory for L-Track)**: E1 + OS/container read-only mounts + tool/network stripping + **6-Point Positive/Negative Probing Verification (I-01 to I-06)**:
    *   *Negative Probe (I-04)*: The tested runtime identity actively attempts to read an existing non-whitelisted dummy file and write to a read-only input file; the system must log an actual `PermissionDenied` error (404 Not Found or timeout does NOT count).
    *   *Positive Probe (I-05)*: Verify the identity can read allowed inputs, write to the output directory, and execute its test runner.

---

# Section 4: Gate-by-Gate Protocol (G0 to G7 — 9 Gate Nodes)

## 4.1 Orthogonal State Triad
In `project_state.json`, state dimensions are strictly separated to prevent state spoofing:
*   `phase`: `G0 | G0.5 | G1 | G2 | G3 | G4 | G5 | G6 | G7 | observing | archived`
*   `execution_state`: `active | awaiting-approval | blocked | rework-required | paused | cancelled | completed`
*   `gate_results`: Each gate independently evaluates to `not-started | in-progress | passed | conditional | failed | waived | not-applicable`

## 4.2 Standard Gate Procedures (Gate-by-Gate Protocol)

### [G0 Initiation] & [G0.5 Requirement Two-Way Confirmation]
1. The Lead Director establishes the project state ledger, recording risk routing (S/M/L), Token/cost budget caps (default: **80% warning threshold, 100% hard stop**), and environmental ground truth baselines (OS, Shell, encoding, working directory).
2. The Lead Director completes the G0.5 restatement in `spec_and_contracts.md` (distinguishing: Owner's verbatim words / Director's inferences / unverified hypotheses), explicitly enumerating **In-Scope (Must-haves)**, **Out-of-Scope (Explicit Won't-haves)**, and structured **Acceptance Criteria (AC, including preconditions, inputs, expected outcomes, and Core/General classification)**.
3. *Technical Unknown Spike Exit*: If technical feasibility is unknown, request a small budget to build a prototype in an isolated sandbox. Upon spike completion, return to G0.5 with factual conclusions; **spike prototype code is strictly prohibited from bypassing quality gates to become production deliverables directly**.
4. **Exit Criterion**: Human Owner explicitly confirms the restatement contents.

### [G1 Design & Three-Tier Contracts]
The Lead Director finalizes the technical design in `spec_and_contracts.md` (and supporting machine-readable contract files), delivering the Three-Tier Contracts:
1. **Tier 1: Data & Interface Contract**: OpenAPI / JSON Schema / TypeScript types and other real machine-readable definition files, verified via automated syntax validation scripts (declare `no-applicable-data-contract` if no structured data exists).
2. **Tier 2: External Behavior & Business Invariants**: State transition matrices, error codes, and business invariants that must never be violated.
3. **Tier 3: Testability Contract (Test Harness)**: Explicit test execution commands, readiness probe criteria, test database reset commands (**strictly forbidden to point to production databases!**), external dependency mocking methods, evidence log locations, and cleanup procedures. For L-Track, an additional **Fuzzing input surface & budget plan** is mandatory.

### [G2 Blind Three-Perspective Peer Review] (S-Track conditionally exemptible; M-Track $\ge 1$ reviewer; L-Track $\ge 2$ reviewers, preferably from heterogeneous model families)
1. `gate_runner` bundles whitelisted read-only materials (including sanitized copies, requirements, and contracts), **stripping the Lead Director's self-evaluation and comments from other reviewers**.
2. Reviewers execute in a clean, stateless session, producing reports across three orthogonal perspectives: **Perspective A (Architecture & Requirements)**, **Perspective B (Security & Reliability)**, and **Perspective C (Simpler Alternatives & Over-Engineering Checks)**. Every finding is tagged as `Blocker | Major | Suggestion` (or `No finding | Insufficient evidence`).
3. Original review reports are archived. The Lead Director responds to every finding in `review_and_defects.yaml` (`Adopted | Partially Adopted | Rejected | Clarification Needed`). The control plane verifies 100% 1-to-1 mapping between finding IDs and responses without omissions.
4. **Exit Criterion**: All `Blocker` findings are revised and resolved (or proven false positives via objective evidence and independently verified). If the Director and Reviewer reach an impasse, after a maximum of **2 rounds**, it must be immediately escalated to the Human Owner for arbitration.

### [G3 Baseline Freeze & Owner Authorization] (Four-Step Anti-Forgery Freeze Method)
1. The Lead Director completes contract and design revisions and halts all file modifications.
2. `gate_runner` calculates byte-level SHA-256 hashes for `spec_and_contracts.md` and contract files, creates the freeze `manifest`, assigns a monotonic sequence `seq`, and computes the root `manifest_sha256`.
3. Present a one-page decision brief to the Human Owner (detailing change diffs, disputed items, permission scopes, and `manifest_sha256`).
4. **Exit Criterion**: After the Owner explicitly replies with approval, `gate_runner approve` records an HMAC-SHA256 signed entry binding the role and `manifest_sha256` in `approvals.jsonl`, synchronized with the external trust anchor `~/.o9-trust/anchor_<ws_id>.sha256`. Any subsequent byte modifications to frozen baseline files trigger immediate control-plane circuit breaking.

> **V1.6.4 control-plane note**: before freezing, `gate_runner.py` enforces that `spec_and_contracts.md` is non-empty and carries structured `AC-xxx` table rows (G1-01). The `manifest` covers `spec_and_contracts.md` plus every contract file under `o9_workspace/contracts/`, and the composite `manifest_sha256` together with the `files[]` listing is signed into the FREEZE record and recomputed by both `approve` and `check` (G3-01/G3-02). The local `.o9_project_id` marker and the `~/.o9-trust/index.tsv` registry pin the workspace-to-project binding and provide the `trust-reset <PROJECT_ID>` disaster-recovery path (G3-03). At G5, `evidence_log_ref` must resolve inside the repository root and be non-empty, the latest QA run is selected by `recorded_at` chronology, and defect/run items are parsed order-independently (G5-02/G5-03).

### [G4 Isolated Development, Concurrency Control & Anti-Stubbing Check]
1. **Write Scope Isolation**: Parallel task tickets must declare explicit `allowed_write_paths`. Concurrent tasks in the same workspace must never have overlapping write paths! Shared configuration files (e.g., dependency manifests, shared types) are assigned to a single current holder for serialized modification.
2. **Anti-Stubbing Scan**: Upon completion of developer self-testing, `gate_runner check` automatically scans the codebase:
   * Rejects incomplete placeholders (`TODO`, `FIXME`, empty functions, bare `pass`) across UTF-8, UTF-16, production, and test files;
   * Cross-checks the Mock & Stub Inventory to ensure mock data and hardcoded fake returns never reach production call paths;
   * Rejects deleted assertions or vacuous assertions (`assert True`, `assert x == x`).
3. **Deterministic Error Circuit Breaker**: When an identical command errors out with no substantial changes in code or environment, blind retry loops are strictly forbidden.
4. **Exit Criterion**: Build generates a unique candidate build identifier `candidate_id` (locking source commit, dependency lockfile, and configuration digest) and hands over to G5.

### [G5 Independent Verification: Black-Box First, Fuzzing & Defect Closed-Loop]
1. **Phase 1: Blindfolded Black-Box Testing (Black-Box First Iron Law)**
   * Launch a fresh, independent QA session with **production source code physically shielded**, providing only approved specifications, ACs, behavioral/testability contracts, and the built `candidate_id` test entrypoint.
   * QA tester freezes first-round black-box test cases, executes normal, boundary, error, and permission test cases, and produces tamper-resistant test execution logs (recording command, exit code, observed behavior, and evidence log path).
2. **Phase 2: Mandatory L-Track Fuzzing & Open-Box White-Box Testing**
   * After black-box conclusions are locked, grant read-only source access for white-box inspection (error paths, concurrency, resource leaks, prompt injection, and tool privilege escalation).
   * L-Track projects must execute fuzzing as planned, verifying not just crash resilience, but business invariant integrity and data consistency.
3. **Phase 3: AI-Unreachable Scenarios -> Manual Verification Todo Card**
   * ACs requiring physical hardware or human sensory/UX verification must remain `not-run` or `blocked` and be recorded on a Manual Verification Card for human completion. AI guessing or marking `passed` is strictly forbidden.
4. **Defect Closed-Loop Iron Law**: Defects follow the lifecycle: `open -> fixing -> ready-for-retest -> closed`. Developers can only advance bugs to `ready-for-retest` and produce a new `candidate_id`; **only the independent QA tester has authority to sign `gate_runner close-bug` to transition a bug to `closed` after verifying fixes and running regression suites**.

### [G6 Technical Acceptance & RTM Reconciliation]
1. In `rtm_acceptance.md`, pull all approved ACs and align line-by-line: source commit, test case ID, execution record `run_id`, coverage status (`covered`), and test outcome (`passed`).
2. **Independent Verification Requirements**:
   * If the Lead Director acted as developer, S/M tracks require the Human Owner or an uninvolved independent session to verify test execution evidence;
   * L-Track projects, regardless of staffing, must initiate a completely fresh **G6 Cross-Review Session** to audit raw logs, specialized evidence, and open defects for critical ACs.
3. **Conditional Acceptance (Conditional Pass)**: If non-blocking flaws (Major/Suggestion) are accepted under known debt, they must be registered in the Conditions Ledger (specifying mitigation constraints, owner, deadline, and overdue shutdown actions). **Blockers and Core AC failures can NEVER be granted conditional pass!**

### [G7 Owner Sign-Off, Decoupled Release & Double-Loop Post-Mortem]
1. The Human Owner makes three independent, decoupled decisions at the end of `rtm_acceptance.md`:
   * ① **Sign-Off Acceptance Decision**: Whether the engineering deliverables meet acceptance standards (`approved | rejected | rework-required`).
   * ② **Release Authorization Decision**: Whether and when the deliverables are authorized for production deployment (`hold | authorized`).
   * ③ **Project Ownership & Open-Source License Decision**: Explicit copyright assignment and license declaration (e.g., MIT, Apache-2.0, Proprietary).
2. Upon release authorization, execute deployment and smoke tests according to the release package.
3. Collect minimal governance metrics (tokens/cost, rejection count, 4-category gate interception attribution, escaped defects), conduct double-loop post-mortem analysis, and determine whether SOP upgrades are warranted.

---

# Section 5: Change Control (C0-C3), 80% Budget Handoff & Emergency Hotfix

## 5.1 Four-Tier Change Control During Development
*   **C0 (In-Implementation Micro-Adjustment)**: No AC change, no interface contract change, no security boundary change $\rightarrow$ Record diffs within task and run test suite; no external authorization required.
*   **C1 (Compatible Contract Extension)**: Backward-compatible extension within original scope with zero risk increase (must verify strict consumers; optional field addition alone does not prove compatibility) $\rightarrow$ If pre-authorized by Human Owner, Lead Director verifies and records derived baseline; if not pre-authorized, submit for quick Owner approval.
*   **C2 (Partial Breaking / Standard Change)**: Incompatible interface change or modified ACs $\rightarrow$ **Immediately halt affected scope**, perform targeted review, and re-freeze G3 baseline with Owner re-approval.
*   **C3 (Major Requirement / Security Redesign)**: Core objectives changed or high-risk escalation triggered $\rightarrow$ **Halt entire project pipeline**, roll back to G0/G0.5/G1 for re-routing and redesign.

## 5.2 Budget Warning & 80% Graceful Handoff
*   When cumulative resource consumption hits the **80% warning threshold**, immediately cease opening new tasks and utilize the remaining 20% **Closing Reserve** to save a **Work Snapshot** at a consistent state.
*   **Snapshot Fidelity Iron Law**: Truthfully record uncommitted changes (`git diff`), pending checks, and unknown side effects; **never roll back or delete incomplete user code to fabricate a "clean snapshot", and never misrepresent a work snapshot as an approved baseline!**
*   Sudden power outages or quota exhaustion may be flagged as `handoff.status: incomplete`; resuming agents must wait for previous write locks to clear and verify on-disk consistency before resuming write operations.

## 5.3 Emergency Hotfix
Reserved strictly for production incidents to mitigate live damage. Execute rollback, shutdown, or minimal fix within pre-authorized operational boundaries; if conditions preclude running full G5 verification on-site, record as **Restricted Emergency Mitigation** (fabricating G5 pass records is prohibited). Within **24 hours** after system stabilization, complete the hotfix incident card, independent retesting, and root-cause post-mortem.

---

# Part 3: Ready-to-Use "Core 4-Artifact" Templates

Initialize an `o9_workspace/` directory in your project with these 4 core files to govern the entire workflow:

```text
o9_workspace/
 ├── project_state.json         # [Core 1] Control plane state machine, active baseline metadata & audit event cache
 ├── spec_and_contracts.md      # [Core 2] G0.5 Two-Way Confirmation + AC Standards + G1 Three-Tier Contracts
 ├── review_and_defects.yaml    # [Core 3] G2 Blind Reviews + Mock Inventory + G5 QA Runs & Defects Ledger
 ├── rtm_acceptance.md          # [Core 4] G6 Requirements Traceability Matrix (RTM) + Conditions + G7 Owner Decisions
 └── approvals.jsonl            # [Decoupled Ledger] Append-only signature ledger (HMAC-SHA256 hash-chained with ~/.o9-trust/)
```

> **Decoupled Ledger & Default-Red Disclosure**: In addition to the four core artifacts, `init` creates an independent, read-only append-only signature ledger **`o9_workspace/approvals.jsonl`** (anchored externally in `~/.o9-trust/` with HMAC-SHA256 hash chains). This completely separates cryptographic approval signatures from the `project_state.json` status cache, eliminating self-hashing circular dependency. All out-of-the-box templates are in a **Default-Red** state (`source_code_hidden_verified: false`, `exit_code: -1`, valid `recorded_at` timestamps, closed statuses strictly `closed / verified`, RTM defaulted to `not-covered / not-run`, and G7 sign-off defaulted to `pending`), preventing zero-work gate bypasses.

---

## Template 1: `o9_workspace/project_state.json` (Control Plane State Machine & Audit Cache)
*(Note: Maintained by `gate_runner.py`; approval signatures live independently in `o9_workspace/approvals.jsonl`)*

```json
{
  "project_id": "PRJ-2026-001",
  "title": "Project Title",
  "sop_version": "O9-RD-Next-V1.6.4",
  "route": "M",
  "state": {
    "phase": "G0",
    "execution_state": "active",
    "gate_results": {
      "G0": "in-progress",
      "G0.5": "not-started",
      "G1": "not-started",
      "G2": "not-started",
      "G3": "not-started",
      "G4": "not-started",
      "G5": "not-started",
      "G6": "not-started",
      "G7": "not-started"
    }
  },
  "active_baseline": {
    "baseline_id": null,
    "parent_baseline_id": null,
    "spec_sha256": null,
    "manifest_sha256": null,
    "files": [],
    "frozen_at": null
  },
  "baseline_history": [],
  "audit_events": []
}
```

---

## Template 2: `o9_workspace/spec_and_contracts.md` (G0.5 Two-Way Confirmation & G1 Three-Tier Contracts)

```markdown
# Requirement Specification & Three-Tier Engineering Contracts (Spec & Contracts)
- **Project ID**: PRJ-2026-001
- **Revision**: v0.1
- **Track**: [ S / M / L ]

## Part 1: G0.5 Requirement Clarification & Two-Way Confirmation
- **Original Request Ref**:
- **Director's Restated Goal**:
- **Must-Have Scope (In-Scope)**:
  1. `[REQ-001]` (Explicit Request / Director Inference)
- **Explicitly Excluded (Out-of-Scope)**:
  1. None
- **Structured Acceptance Criteria (AC)**:
| AC-ID | REQ-ID | Importance | Preconditions | Input / Action | Expected Result & Failure Behavior | Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `AC-001` | `REQ-001` | `core` | Service running | Valid input | Returns 200 OK | `automated` |
- **Owner Confirmation**: Approved

## Part 2: G1 Architecture & Three-Tier Contracts
### 2.1 Design Summary & Rollback Plan
### 2.2 Tier 1: Data & Interface Contract (Schema)
- **Applicability**: `applicable`
### 2.3 Tier 2: External Behavior & Business Invariants
### 2.4 Tier 3: Testability Contract (Test Harness for G5 QA)
- **Working Dir & Startup Command**: `pytest`
- **Readiness Condition**: Exit code 0
- **Synthetic Data Reset Command**: N/A
```

---

## Template 3: `o9_workspace/review_and_defects.yaml` (G2 Blind Reviews, Mock Inventory & G5 Defects Ledger)

```yaml
project_id: PRJ-2026-001
bound_baseline_id: BL-001

# 1. G2 Blind Three-Perspective Review Ledger
g2_reviews:
  review_pack_sha256: null
  reviewers:
    - reviewer_id: REV-SESSION-01
      isolation_level: E1
      perspectives_checked:
        A_architecture_and_req: "Checked"
        B_security_and_reliability: "Checked"
        C_simpler_alternatives: "No finding"
  findings_disposition:
    - finding_id: REV-R1-B-001
      perspective: B
      severity: Major
      director_disposition: "Adopted"
      resolved: true

# 2. G4 Mock & Stub Inventory (Must be unreachable in production)
mock_and_stub_inventory:
  - item_id: MOCK-001
    location: "tests/mocks/mock_service.py"
    prod_unreachable_verified: true

# 3. G5 Independent QA Runs (Black-Box First Iron Law)
g5_test_runs:
  - run_id: RUN-BB-001
    recorded_at: "2026-11-03T00:00:00Z"
    phase_type: "black-box-first"
    tester_session: "QA-SESSION-01"
    source_code_hidden_verified: false
    candidate_id: "CAND-001"
    command_executed: "pytest tests/"
    exit_code: -1
    evidence_log_ref: "o9_workspace/evidence/run-bb-001.log"

# 4. Defects Ledger (Allowed closed statuses: closed, verified)
defects: []

# 5. Manual Verification Todos (For hardware/real-device UX unreachable by AI)
manual_verification_todos: []
```

---

## Template 4: `o9_workspace/rtm_acceptance.md` (G6 Full RTM Reconciliation & G7 Owner Decisions)

```markdown
# G6 Requirements Traceability Matrix (RTM) & G7 Sign-Off Decisions
- **Project ID**: PRJ-2026-001
- **Bound Baseline**: `BL-001`
- **Candidate ID**: `CAND-001`

## 1. Full Requirements Traceability Matrix (RTM)
| REQ-ID | AC-ID | Importance | Code Ref | Test Case ID | Evidence `run_id` | Coverage | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-001` | `AC-001` | `core` | `src/` | `BB-001` | `RUN-BB-001` | `covered` | `passed` |

## 2. Conditions Ledger (No Blockers Allowed)
- None

## 3. G6 Technical Acceptance & Independent Audit Verdict
- **Director Verdict**: `passed`
- **Independent Auditor Verdict**: `passed`

## 4. G7 Owner's Three Decoupled Decisions
- **Decision 1 (Sign-Off)**: `pending`
- **Decision 2 (Release Authorization)**: `hold`
- **Decision 3 (Ownership & License)**: `MIT`
```

---

# Part 4: Agent Role Wake-Up System Prompts

*   **Director Agent Prompt**: *"You are the O9-RD Director. Read `project_state.json` and `spec_and_contracts.md`. Rule: Never write business code before G0.5 is explicitly confirmed by the Owner! First evaluate S/M/L risk routing and output the G0.5 Two-Way Confirmation (Goal, In-Scope, Out-of-Scope, AC table)."*
*   **G2 Blind Reviewer Prompt (Fresh Session)**: *"You are an independent G2 Reviewer in a clean session. Read ONLY `spec_and_contracts.md`. Do not flatter. Critique strictly across Perspective A (Architecture/Req Fit), Perspective B (Security/Reliability), and Perspective C (Simpler Alternatives). Classify findings as Blocker, Major, or Suggestion."*
*   **G4 Coder Prompt**: *"You are a G4 Developer. Modify ONLY files within your authorized `allowed_write_paths`. Never modify `spec_and_contracts.md`, never leave `TODO` stubs or hardcoded mock returns in production paths, and never delete test assertions. Report `candidate_id` and self-test outputs upon completion."*
*   **G5 Black-Box QA Prompt (Fresh Session)**: *"You are the independent G5 QA Tester. IRON LAW (Black-Box First): In Phase 1, you are strictly forbidden from reading `src/` implementation code! Design and execute black-box tests based solely on `spec_and_contracts.md` and the §2.4 Test Harness. Mark unreachable hardware/UX checks as `not-run` in a Manual Verification Todo Card—never guess `passed`. Only after Phase 1 results are locked may you inspect `src/` for white-box/fuzz testing."*
