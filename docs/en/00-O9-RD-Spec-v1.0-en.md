# 🛠️ O9-RD Next V1.0 | Master Workflow Specification & 4-Artifact Templates (English Edition)

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

# Part 3: Ready-to-Use "Core 4-Artifact" Templates

Initialize an `o9_workspace/` directory in your project with these 4 files:

## Template 1: `o9_workspace/project_state.json` (Control Plane Ledger)
```json
{
  "project_id": "PRJ-2026-001",
  "title": "Project Title",
  "sop_version": "O9-RD-Next-V1.0",
  "route": null,
  "risk_flags": {
    "auth_or_permission_change": null,
    "sensitive_data_or_secret": null,
    "irreversible_data_op": null,
    "money_or_billing": null,
    "broad_prod_impact": null,
    "agent_external_side_effect": null,
    "core_architecture_change": null
  },
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
  "budgets": {
    "token_limit": 500000,
    "token_used": 0,
    "warning_ratio": 0.8,
    "hard_stop_ratio": 1.0,
    "review_escalation_max_rounds": 2
  },
  "active_baseline": {
    "baseline_id": null,
    "manifest_sha256": null,
    "files": [
      { "path": "o9_workspace/spec_and_contracts.md", "bytes": null, "sha256": null }
    ]
  },
  "detached_approvals": [
    {
      "approval_id": "APR-G3-001",
      "gate": "G3",
      "decision": "pending",
      "approver": "HumanOwner",
      "decided_at": null,
      "bound_manifest_sha256": null,
      "authorized_write_scopes": []
    }
  ],
  "workstreams_and_locks": [
    {
      "task_id": "TASK-01",
      "owner_agent": "Coder-A",
      "allowed_write_paths": ["src/module_a/**"],
      "shared_resources_locked": ["port:8081"],
      "candidate_id": null
    }
  ],
  "handoff": {
    "status": "not-required",
    "work_snapshot_id": null,
    "uncommitted_diff_ref": null,
    "write_lock_released": false
  }
}
```

## Template 2: `o9_workspace/spec_and_contracts.md` (G0.5 & G1 Master Spec)
```markdown
# Requirement Specification & Three-Tier Engineering Contracts
- **Project ID**: PRJ-2026-001 | **Revision**: v0.1 | **Track**: [ S / M / L ]

## Part 1: G0.5 Requirement Clarification & Two-Way Confirmation
- **Original Request Ref**:
- **Director's Restated Goal**:
- **Must-Have Scope (In-Scope)**:
  1. `[REQ-001]` (Source: Explicit Owner Request / Director Inference)
- **Explicitly Excluded (Out-of-Scope)**:
  1.
- **Structured Acceptance Criteria (AC)**:
| AC-ID | REQ-ID | Core/General | Preconditions | Input / Action | Expected Result & Failure Behavior | Verification Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `AC-001` | `REQ-001` | `core` | | | | `automated` |
- **Owner Confirmation (Pre-Freeze)**: [ Approved / Needs Revision ]

## Part 2: G1 Architecture & Three-Tier Contracts
### 2.1 Design Summary, Trade-offs & Rollback Plan
### 2.2 Tier 1: Data & Interface Contract (Schema)
- **Applicability**: [ `applicable` / `no-applicable-data-contract` ]
- **Schema Definition & Validation Result**:
### 2.3 Tier 2: External Behavior & Business Invariants
### 2.4 Tier 3: Testability Contract (Test Harness for G5 QA)
- **Working Dir & Startup Command**:
- **Readiness Probe Condition**:
- **Required Env Var Names (NO secret values!)**:
- **Synthetic Data Setup & Reset Command (Test DB only)**:
- **External Dependency Mocks (Must be unreachable in prod)**:
- **L-Track Mandatory Fuzzing Plan**: Target surfaces, fuzzer tool, budget, failure oracles.
```

## Template 3: `o9_workspace/review_and_defects.yaml` (G2 Reviews & G5 Bugs)
```yaml
project_id: PRJ-2026-001
bound_baseline_id: BL-001

g2_reviews:
  reviewers:
    - reviewer_id: REV-01
      isolation_level: E1
      perspectives:
        A_architecture_fit: "Checked"
        B_security_reliability: "Checked"
        C_simpler_alternatives: "No finding"
  findings_disposition:
    - finding_id: REV-R1-B-001
      severity: Blocker # Blocker / Major / Suggestion
      director_disposition: "Adopted"
      resolved: true

mock_and_stub_inventory:
  - item_id: MOCK-001
    location: "tests/mocks/mock_service.py"
    prod_unreachable_verified: true

g5_test_runs:
  - run_id: RUN-BB-001
    phase_type: "black-box-first"
    source_code_hidden_verified: true
    candidate_id: "CAND-git-a1b2c3d"
    command_executed: "pytest tests/blackbox/"
    exit_code: 0
    evidence_log_ref: "tests/evidence/run-bb-001.log"

defects:
  - bug_id: BUG-001
    related_ac: AC-001
    severity: Blocker
    status: "open" # open -> fixing -> ready-for-retest -> closed (Only QA can set closed!)
    closed_by_tester: null

manual_verification_todos: []
```

## Template 4: `o9_workspace/rtm_acceptance.md` (G6 RTM & G7 Sign-Off)
```markdown
# G6 Requirements Traceability Matrix (RTM) & G7 Decisions
- **Bound Baseline**: `BL-001` (`manifest_sha256: ...`) | **Candidate ID**: `CAND-...`

## 1. Full Requirements Traceability Matrix
| REQ-ID | AC-ID | Core/General | Implementation Commit/Path | Test Case ID | Evidence `run_id` | Coverage | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `REQ-001` | `AC-001` | `core` | | `BB-001` | `RUN-BB-001` | `covered` | `passed` |

## 2. G6 Technical Acceptance & Independent Audit Conclusion
- **Director Verdict**: [ Passed / Conditional / Failed ]
- **Independent Auditor Verification (Mandatory if Director coded or L-Track)**:

## 3. G7 Owner's Three Decoupled Decisions
1. **Sign-Off**: [ Approved / Rework ]
2. **Release Authorization**: [ Hold / Authorized for Prod Release ]
3. **Ownership & License**: [ MIT / Internal / Archived ]
```

---

# Part 4: Agent Role Wake-Up System Prompts

*   **Director Agent Prompt**: *"You are the O9-RD Director. Read `project_state.json` and `spec_and_contracts.md`. Rule: Never write business code before G0.5 is explicitly confirmed by the Owner! First evaluate S/M/L risk routing and output the G0.5 Two-Way Confirmation (Goal, In-Scope, Out-of-Scope, AC table)."*
*   **G2 Blind Reviewer Prompt (Fresh Session)**: *"You are an independent G2 Reviewer in a clean session. Read ONLY `spec_and_contracts.md`. Do not flatter. Critique strictly across Perspective A (Architecture/Req Fit), Perspective B (Security/Reliability), and Perspective C (Simpler Alternatives). Classify findings as Blocker, Major, or Suggestion."*
*   **G4 Coder Prompt**: *"You are a G4 Developer. Modify ONLY files within your authorized `allowed_write_paths`. Never modify `spec_and_contracts.md`, never leave `TODO` stubs or hardcoded mock returns in production paths, and never delete test assertions. Report `candidate_id` and self-test outputs upon completion."*
*   **G5 Black-Box QA Prompt (Fresh Session)**: *"You are the independent G5 QA Tester. IRON LAW (Black-Box First): In Phase 1, you are strictly forbidden from reading `src/` implementation code! Design and execute black-box tests based solely on `spec_and_contracts.md` and the §2.4 Test Harness. Mark unreachable hardware/UX checks as `not-run` in a Manual Verification Todo Card—never guess `passed`. Only after Phase 1 results are locked may you inspect `src/` for white-box/fuzz testing."*
