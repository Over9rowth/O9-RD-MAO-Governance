# 🛡️ O9-RD-MAO-Governance

**Verifiable Minimal Control Plane & Software Engineering Governance for Multi-Agent Coding Workflows.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/O9--RD-v1.6-brightgreen.svg)](./docs/en/00-O9-RD-Spec-v1.0-en.md)
[![Zero Dependencies](https://img.shields.io/badge/Control%20Plane-Python%20Stdlib-yellow.svg)](./gate_runner.py)
[![Control Matrix](https://img.shields.io/badge/Control%20Matrix-9%20Gates%20Mapped-orange.svg)](./docs/CONTROL-MATRIX.md)
[![Author](https://img.shields.io/badge/Author-Over9rowth-purple.svg)](https://github.com/Over9rowth)

🌐 **English** | [🇨🇳 简体中文](./README_ZH.md)

---

## Why O9-RD?

"Wild" multi-agent coding setups (treating LLMs like a group chat) fail in production due to **requirement hallucination**, **mutual flattery (sycophancy)**, and **reward hacking** (agents deleting test assertions, writing `TODO` stubs, or secretly lowering acceptance criteria).

> **📌 Control Plane Scope & Engineering Honesty**: `gate_runner.py` (v1.6) provides a **verifiable minimal control plane**: G3 baseline lock (hash-chained HMAC trust root + `~/.o9-trust/` external key-fingerprint pinning & monotonic sequence) + G4 anti-stub/fake-assert scan (including `tests/` & `.ipynb`, UTF-8 & UTF-16 BOM) + cryptographic bug closure signatures (`close-bug`) + G5/G6 structural ledger, real non-empty evidence file & independent QA closer label binding & HMAC BUG_CLOSE record + G7 3-decision sign-off check. **A signing secret ($\ge 16$ characters) must be supplied via `O9_APPROVAL_SECRET` (or `--key`); operations fail-closed when no secret is configured.** Full control mappings (tool-enforced vs manual-verified vs infra-boundary) and same-UID threat model limitations are documented in [`docs/CONTROL-MATRIX.md`](./docs/CONTROL-MATRIX.md). G2 semantic peer review, container-level E2 sandboxing, and production release execution remain governed by the SOP protocols and IDE rules.

**O9-RD** tames non-deterministic coding agents using a **verifiable deterministic software engineering control plane**:
- 🔒 **G0.5 Two-Way Confirmation & G3 SHA-256 Baseline Lock**: Freeze specs and schemas cryptographically before coding. Agents cannot alter the exam paper to pass tests.
- 🚦 **Risk-First Routing (`S / M / L` Tracks)**: 2-touchpoint fast track for UI/copy tweaks (`S`), full contract review for features (`M`), and strict sandbox + fuzzing for Auth/Billing/DB ops (`L`).
- 🙈 **G5 Black-Box Testing First**: QA agents run in clean sessions **without read access to `src/`**, testing purely against the frozen contract before white-box inspection.
- 🚫 **Verifiable Minimal Control Plane CLI (`gate_runner.py` v1.6)**: Monotonic sequence and key-fingerprint pinning, cryptographic `close-bug` signature binding, fail-closed anti-stubbing, independent QA closer label binding & HMAC BUG_CLOSE record, and full control enforcement mapping in [CONTROL-MATRIX.md](./docs/CONTROL-MATRIX.md).

---

## ⚡ Quick Start (30 Seconds)

### Option A: Drop-in Rules for Cursor / Claude Code / Windsurf
Copy [`.cursorrules`](./.cursorrules) or [`CLAUDE.md`](./CLAUDE.md) into your project root to immediately enforce G0.5 confirmation, anti-stubbing, and black-box verification.

### Option B: Run the Deterministic Control Plane CLI
Zero third-party dependencies (pure Python 3 standard library):
```bash
# 1. Initialize workspace (copies full 4-artifact templates + read-only approvals.jsonl)
python gate_runner.py init

# 2. Freeze G3 spec baseline (writes HMAC-signed record & pins key fingerprint)
O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py freeze

# 3. Bind detached human approval signature (requires valid role & secret)
O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py approve station_master

# 4. Cryptographically sign bug closure in approvals.jsonl (requires defect to exist in YAML first)
O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py close-bug BUG-001 qa_lead

# 5. Run fail-closed G5 verification (verifies HMAC trust root, blocks TODOs/fake asserts & open bugs)
O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py check ./src --gate=G5 --require-approval
```

### Option C: Interactive Workflow Customizer (Meta-Prompt)
Paste [`prompts/MAO-Workflow-Coach-en.md`](./prompts/MAO-Workflow-Coach-en.md) into Claude or ChatGPT. Answer 4 short questions about your tech stack, and it will generate a custom, right-sized multi-agent workflow for your repo.

---

## 🏗️ Architecture (G0–G7 State Machine)

```mermaid
flowchart LR
    G0["<b>G0 Route</b><br/>S / M / L Track"] --> G05["<b>G0.5 Confirm</b><br/>In/Out Scope & AC"]
    G05 --> G1["<b>G1 Contracts</b><br/>Schema & Harness"]
    G1 --> G2["<b>G2 Blind Review</b><br/>A.Arch / B.Sec / C.Simple"]
    G2 --> G3["<b>G3 SHA-256 Lock</b><br/>Detached Approval"]
    G3 --> G4["<b>G4 Scoped Code</b><br/>No TODO / Write Lock"]
    G4 --> G5["<b>G5 Black-Box QA</b><br/>Source Hidden First"]
    G5 -->|"Bug (Coder!=Close)"| G4
    G5 --> G6["<b>G6 RTM Audit</b><br/>Traceability Matrix"]
    G6 --> G7["<b>G7 Sign-off</b><br/>Decoupled Release"]
```

---

## 📂 Repository Structure

```text
├── gate_runner.py               # Deterministic control-plane CLI (init / freeze / approve / close-bug / check)
├── .cursorrules / CLAUDE.md     # Drop-in governance rules for AI IDEs
├── templates/                   # Full 4-artifact templates (JSON/YAML/MD)
├── prompts/                     # Interactive Agile MAO Coach Meta-Prompts (EN & ZH)
└── docs/
    ├── CONTROL-MATRIX.md                        # Control Implementation Matrix & Threat Model
    ├── en/00-O9-RD-Spec-v1.0-en.md              # Full English SOP & Agent Prompts
    └── zh/                                      # Full Chinese SOP & 14-Chapter Textbook
```

## 📜 License
MIT License © 2026 **曾威长 (Over9rowth)**
