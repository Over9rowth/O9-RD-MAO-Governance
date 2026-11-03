# 🛡️ O9-RD-MAO-Governance

**可验证的最小软件工程控制面与多智能体（Multi-Agent）研发治理框架。**  
*(Verifiable Minimal Control Plane & Software Engineering Governance for Multi-Agent Coding Workflows.)*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/O9--RD-v1.6.4-brightgreen.svg)](./docs/zh/00-O9-RD-Spec-v1.0-zh.md)
[![Zero Dependencies](https://img.shields.io/badge/Control%20Plane-Python%20Stdlib-yellow.svg)](./gate_runner.py)
[![Control Matrix](https://img.shields.io/badge/Control%20Matrix-9%20Gates%20Mapped-orange.svg)](./docs/CONTROL-MATRIX.md)
[![Author](https://img.shields.io/badge/Author-曾威长%2FOver9rowth-purple.svg)](https://github.com/Over9rowth)

[🌐 English](./README.md) | 🇨🇳 **简体中文**

---

## 核心解决什么痛点？

野生多智能体协作（群聊式 AI 写代码）在真实工程中极易死于**需求脑补放大**、**商业互吹**与**作弊通关（删 `assert` 断言、写 `TODO` 假实现、偷改需求文档降低标准）**。

> **📌 控制面边界与诚实声明**：`gate_runner.py` (v1.6.4) 提供**可验证的最小控制面**：G1 非空规范 + 结构化 `AC-xxx` 表行校验 + G3 基线锁（对 `spec_and_contracts.md` 与 `o9_workspace/contracts/**` 全部文件计算复合 `manifest_sha256`，叠加链式 HMAC 签名信任根、`~/.o9-trust/` 外部密钥指纹与单调序号钉死）+ G4 反占位/假断言扫描（含 `.ipynb` 与 `tests/`，支持 UTF-8 及 UTF-16 BOM，全树扫描无目录排除）+ 缺陷加密关单签名绑定（`close-bug`，杜绝幽灵预签）+ G5 仓库内证据文件约束、按 `recorded_at` 时序选取最新 QA 运行、独立 QA 关单身份标签绑定及 HMAC BUG_CLOSE 记录 + G6 结构化 RTM 表行校验与 QA `run_id` 对账 + G7 三项签收决定校验，并提供 `.o9_project_id` 与 `~/.o9-trust/index.tsv` 本地注册表及 `trust-reset` 恢复通道（G3-03）。**签名密钥（$\ge 16$ 位字符）须由环境变量 `O9_APPROVAL_SECRET`（或 `--key`）提供；无密钥环境下拒绝执行签名与核验操作（Fail-Closed）。** 每一道门禁控制落地的严格分类（tool-enforced vs tool-validated vs manual-verified vs infra-boundary）详见 [《控制落实矩阵 (CONTROL-MATRIX.md)》](./docs/CONTROL-MATRIX.md)，且每一条 `tool-enforced` 声明均由 `tests/test_v16_controls.py` 实测覆盖。G2 语义架构盲评、容器级 E2 沙箱隔离、抵御同 UID 代理窃取密钥的密钥托管，以及生产环境发布操作，则作为配套 SOP 流程、IDE 规则与 CI 托管约束执行。

**O9-RD** 将传统软件工程治理引入 AI 编程：
- 🔒 **G0.5 双向复述 & G3 SHA-256 防伪锁死**：动工前先复述“做什么/不做什么”；契约经批准后计算字节级 SHA-256 指纹写入只读信任根，严禁 AI 打不过就偷改考卷。
- 🚦 **风险一票否决路由（`S / M / L` 三轨）**：改文案样式走 `S` 轨（两次触点极速通关）；常规开发走 `M` 轨；触及鉴权/资金/删库强制走 `L` 轨（E2 沙箱 + 强制 Fuzzing）。
- 🙈 **G5 黑盒测试先行铁律**：独立测试 Agent 在第一阶段**物理屏蔽业务源码（`src/`）**，仅凭契约测试外部行为，锁死结果后才准看源码做白盒检查；开发严禁自己关闭 Bug。
- 🚫 **可验证极简控制面 CLI（`gate_runner.py` v1.6.4）**：多文件 `manifest_sha256` 基线锁、单调序号与密钥指纹钉死、加密关单签名绑定、按 `recorded_at` 时序约束的仓库内证据、`trust-reset` 恢复通道、独立 QA 关单身份标签绑定及 HMAC BUG_CLOSE 记录，全量 9 道门禁控制边界详见 [CONTROL-MATRIX.md](./docs/CONTROL-MATRIX.md)。

---

## ⚡ 30 秒快速上手 (Quick Start)

1. **Cursor / Claude Code / Windsurf 用户即插即用**：
   直接将根目录的 [`.cursorrules`](./.cursorrules) 或 [`CLAUDE.md`](./CLAUDE.md) 复制到你的项目根目录即可生效。
2. **使用确定性控制面命令行工具（`gate_runner.py`）**：
   ```bash
   # 1. 一键初始化工作区（拷贝完整 4-artifact 模板，钉死 .o9_project_id 与本地 index.tsv 注册表）
   python gate_runner.py init

   # 2. 冻结 G3 需求契约基线（拦截空规范/缺失 AC-xxx 表行；签入 spec_sha256 与复合 manifest_sha256）
   O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py freeze

   # 3. 绑定外部独立签名批准（同时绑定 spec 与 manifest 指纹；基线在冻结后被改动则拒绝批准）
   O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py approve station_master

   # 4. 对修复缺陷进行加密关单签名绑定（须先在 YAML 中存在该缺陷；条目键序任意）
   O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py close-bug BUG-001 qa_lead

   # 5. 执行 Fail-Closed G5 门禁验证（信任根 + manifest + 仓库内证据 + 按 recorded_at 选最新运行）
   O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py check ./src --gate=G5 --require-approval

   # 6. 仅用于灾后恢复：外部信任锚丢失/锁死时重建信任（归档旧锚点与旧账本，而非静默删除）
   O9_APPROVAL_SECRET="my-super-secret-key-16" python gate_runner.py trust-reset PRJ-2026-001
   ```

   > 💡 放在 `o9_workspace/contracts/` 下的接口契约文件会自动纳入 G3 `manifest_sha256`，冻结后任何改动都会在 `approve` 与 `check` 阶段熔断。
3. **让 AI 教练为你量身裁剪极简工作流**：
   复制 [`prompts/MAO-Workflow-Coach-zh.md`](./prompts/MAO-Workflow-Coach-zh.md) 发给 Claude/GPT，回答 4 个小问题即可获得定制方案。

---

## 📚 完整文档与三卷蓝皮书导航 (`docs/` & `prompts/`)

- 📊 **[《控制落实矩阵与威胁模型 (CONTROL-MATRIX.md)》](./docs/CONTROL-MATRIX.md)**
- 🛠️ **[《O9-RD Next V1.0 完整规范与实战模板》](./docs/zh/00-O9-RD-Spec-v1.0-zh.md)** | **[English Spec](./docs/en/00-O9-RD-Spec-v1.0-en.md)**
- 🤖 **[《程序员 MAO 工作流定制教练 · Meta-Prompt》](./prompts/MAO-Workflow-Coach-zh.md)** | **[English Meta-Prompt](./prompts/MAO-Workflow-Coach-en.md)**
- 📕 **[《第一卷：破雾与筑基篇 (第 1~5 章)》](./docs/zh/01-Guide-Part1-Foundations.md)**
- 📗 **[《第二卷：空间状态与流程质量篇 (第 6~11 章)》](./docs/zh/02-Guide-Part2-State-and-Quality.md)**
- 📘 **[《第三卷：安全韧性演进篇与实战附录 (第 12~14 章 + 附录)》](./docs/zh/03-Guide-Part3-Security-and-Evolution.md)**

## 📜 开源协议
MIT License © 2026 **曾威长/Over9rowth**
