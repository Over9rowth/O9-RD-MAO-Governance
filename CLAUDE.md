# O9-RD Multi-Agent Engineering Governance Rules (V1.6.4 — .cursorrules / CLAUDE.md)

You operate under the **O9-RD Software Engineering Governance Protocol (V1.6.4)**:

1. **G0.5 Two-Way Confirmation First**: Never write or modify business code immediately upon receiving a vague request. First restate: (a) Goal, (b) In-Scope, (c) Out-of-Scope, and (d) Structured Acceptance Criteria (`AC-001` with `automated` or `manual` mode). Wait for explicit user confirmation.
2. **Default-Red & G1/G3 Baseline Lock**: All initial test/RTM states start as RED (`false`, `exit_code: -1`, `not-run`, `pending`). Update `o9_workspace/spec_and_contracts.md` and `o9_workspace/contracts/` before coding. Never alter locked `AC-xxx` criteria or forge `approvals.jsonl` signatures to make failing checks pass.
3. **G4 Scoped Write & Zero Stubbing**: Modify only files within the agreed scope. Never leave `TODO`/`FIXME`/`PLACEHOLDER` comments, `pass`/`...`/`return None` stub functions, or vacuous assertions (`assert True`, `assert x == x`, `assertEqual(1, 1)`).
4. **G5 Black-Box Verification First**: When acting as QA/Tester in a fresh session, test strictly against the external contract and test harness BEFORE inspecting `src/` implementation code. Record genuine ISO-8601 `recorded_at` timestamps (`>= frozen_at`) and repo-internal non-empty evidence logs. Developers cannot mark their own bugs as closed.
5. **G6/G7 Traceability & Decoupled Release**: Every `AC-xxx` row in `rtm_acceptance.md` must link to a valid passing `RUN-xxx` ID (unless explicitly declared `manual` in the frozen spec). Passing QA (`Sign-Off`) never auto-authorizes production deployment (`Release Authorization`) without a dedicated G7 approval.
