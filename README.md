# 🛡️ O9-RD-MAO-Governance

**Verifiable Software Engineering Governance & Minimal Control Plane for Multi-Agent Coding Workflows.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/O9--RD-v1.2-brightgreen.svg)](./docs/en/00-O9-RD-Spec-v1.0-en.md)
[![Zero Dependencies](https://img.shields.io/badge/Control%20Plane-Python%20Stdlib-yellow.svg)](./gate_runner.py)
[![Author](https://img.shields.io/badge/Author-Over9rowth-purple.svg)](https://github.com/Over9rowth)

🌐 **English** | [🇨🇳 简体中文](./README_ZH.md)

---

## Why O9-RD?

"Wild" multi-agent coding setups (treating LLMs like a group chat) fail in production due to **requirement hallucination**, **mutual flattery (sycophancy)**, and **reward hacking** (agents deleting test assertions, writing `TODO` stubs, or secretly lowering acceptance criteria).

> **Engineering Honesty & Scope**: `gate_runner.py` v1.2 provides a **verifiable minimal control plane** enforcing **G3 SHA-256 baseline locking with HMAC-authenticated `approvals.jsonl` trust root**, **G4 anti-stubbing / fake-assertion blocking**, and **G5/G6 fail-closed ledger whitelist assertions**. Higher-level semantic architecture review (G2), container-level E2 sandboxing, and G7 production release separation are governed via the accompanying SOP protocols and IDE rules.

**O9-RD** tames non-deterministic coding agents using a **100% deterministic software engineering control plane**:
- 🔒 **G0.5 Two-Way Confirmation & G3 SHA-256 Baseline Lock**: Freeze specs and schemas cryptographically before coding. Agents cannot alter the exam paper to pass tests.
- 🚦 **Risk-First Routing (`S / M / L` Tracks)**: 2-touchpoint fast track for UI/copy tweaks (`S`), full contract review for features (`M`), and strict sandbox + fuzzing for Auth/Billing/DB ops (`L`).
- 🙈 **G5 Black-Box Testing First**: QA agents run in clean sessions **without read access to `src/`**, testing purely against the frozen contract before white-box inspection.
- 🚫 **Verifiable Minimal Control Plane CLI (`gate_runner.py` v1.2)**: Independent append-only HMAC trust root, fail-closed anti-stubbing, and structural whitelist verification.

---

## ⚡ Quick Start (30 Seconds)

### Option A: Drop-in Rules for Cursor / Claude Code / Windsurf
Copy [`.cursorrules`](./.cursorrules) or [`CLAUDE.md`](./CLAUDE.md) into your project root to immediately enforce G0.5 confirmation, anti-stubbing, and black-box verification.

### Option B: Run the Deterministic Control Plane CLI
Zero third-party dependencies (pure Python 3 standard library):
```bash
# 1. Initialize workspace (copies full 4-artifact templates + read-only approvals.jsonl)
python gate_runner.py init

# 2. Freeze G3 spec baseline (writes HMAC-signed record to approvals.jsonl)
O9_APPROVAL_SECRET="my-secret" python gate_runner.py freeze

# 3. Bind detached human approval signature (requires valid role & secret)
O9_APPROVAL_SECRET="my-secret" python gate_runner.py approve station_master

# 4. Run fail-closed G5 verification (verifies HMAC trust root, blocks TODOs/fake asserts & open bugs)
O9_APPROVAL_SECRET="my-secret" python gate_runner.py check ./src --gate=G5 --require-approval
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
├── gate_runner.py               # Deterministic control-plane CLI (init / freeze / approve / check)
├── .cursorrules / CLAUDE.md     # Drop-in governance rules for AI IDEs
├── templates/                   # Full 4-artifact templates (JSON/YAML/MD)
├── prompts/                     # Interactive Agile MAO Coach Meta-Prompts (EN & ZH)
└── docs/
    ├── en/00-O9-RD-Spec-v1.0-en.md              # Full English SOP & Agent Prompts
    └── zh/                                      # Full Chinese SOP & 14-Chapter Textbook
```

## 📜 License
MIT License © 2026 **曾威长 (Over9rowth)**
