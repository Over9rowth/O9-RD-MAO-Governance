# 🛡️ O9-RD-MAO-Governance

**可验证的软件工程治理与极简确定性控制面（面向多智能体 Multi-Agent 研发工作流）。**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/O9--RD-v1.2-brightgreen.svg)](./docs/zh/00-O9-RD-Spec-v1.0-zh.md)
[![Zero Dependencies](https://img.shields.io/badge/Control%20Plane-Python%20Stdlib-yellow.svg)](./gate_runner.py)
[![Author](https://img.shields.io/badge/Author-曾威长%2FOver9rowth-purple.svg)](https://github.com/Over9rowth)

[🌐 English](./README.md) | 🇨🇳 **简体中文**

---

## 核心解决什么痛点？

野生多智能体协作（群聊式 AI 写代码）在真实工程中极易死于**需求脑补放大**、**商业互吹**与**作弊通关（删 `assert` 断言、写 `TODO` 假实现、偷改需求文档降低标准）**。

> **工程诚实度与控制面边界说明**：`gate_runner.py` v1.2 提供了**可验证的极简确定性控制面**，核心负责强制执行 **G3 契约 SHA-256 基线锁死与基于追加写 `approvals.jsonl` 的 HMAC 独立信任根**、**G4 扫描拦截 TODO 占位与伪造断言**，以及 **G5/G6 台账删除 Fail-Closed 与缺陷状态白名单断言**。更高级别的语义架构盲评（G2）、容器级 E2 沙箱隔离探测与 G7 生产发布分离决策，通过配套的 SOP 规约与 IDE 规则驱动执行。

**O9-RD** 将传统软件工程治理引入 AI 编程：
- 🔒 **G0.5 双向复述 & G3 SHA-256 防伪锁死**：动工前先复述“做什么/不做什么”；契约经批准后计算字节级 SHA-256 指纹写入只读信任根，严禁 AI 打不过就偷改考卷。
- 🚦 **风险一票否决路由（`S / M / L` 三轨）**：改文案样式走 `S` 轨（两次触点极速通关）；常规开发走 `M` 轨；触及鉴权/资金/删库强制走 `L` 轨（E2 沙箱 + 强制 Fuzzing）。
- 🙈 **G5 黑盒测试先行铁律**：独立测试 Agent 在第一阶段**物理屏蔽业务源码（`src/`）**，仅凭契约测试外部行为，锁死结果后才准看源码做白盒检查；开发严禁自己关闭 Bug。
- 🚫 **可验证极简控制面 CLI（`gate_runner.py` v1.2）**：独立 HMAC 审计流、Fail-Closed 防御与结构化白名单状态核验。

---

## ⚡ 30 秒快速上手 (Quick Start)

1. **Cursor / Claude Code / Windsurf 用户即插即用**：
   直接将根目录的 [`.cursorrules`](./.cursorrules) 或 [`CLAUDE.md`](./CLAUDE.md) 复制到你的项目根目录即可生效。
2. **使用确定性控制面命令行工具（`gate_runner.py`）**：
   ```bash
   # 1. 一键初始化工作区（拷贝完整 4-artifact 模板及只读 approvals.jsonl）
   python gate_runner.py init

   # 2. 冻结 G3 需求契约基线（向 approvals.jsonl 写入 HMAC 签名记录）
   O9_APPROVAL_SECRET="my-secret" python gate_runner.py freeze

   # 3. 绑定外部独立签名批准（校验角色权限与 HMAC 密钥）
   O9_APPROVAL_SECRET="my-secret" python gate_runner.py approve station_master

   # 4. 执行 Fail-Closed G5 门禁验证（校验信任根防篡改、拦截 TODO/fake-assert 及未关闭缺陷）
   O9_APPROVAL_SECRET="my-secret" python gate_runner.py check ./src --gate=G5 --require-approval
   ```
3. **让 AI 教练为你量身裁剪极简工作流**：
   复制 [`prompts/MAO-Workflow-Coach-zh.md`](./prompts/MAO-Workflow-Coach-zh.md) 发给 Claude/GPT，回答 4 个小问题即可获得定制方案。

---

## 📚 完整文档与三卷蓝皮书导航 (`docs/` & `prompts/`)

- 🛠️ **[《O9-RD Next V1.0 完整规范与实战模板》](./docs/zh/00-O9-RD-Spec-v1.0-zh.md)** | **[English Spec](./docs/en/00-O9-RD-Spec-v1.0-en.md)**
- 🤖 **[《程序员 MAO 工作流定制教练 · Meta-Prompt》](./prompts/MAO-Workflow-Coach-zh.md)** | **[English Meta-Prompt](./prompts/MAO-Workflow-Coach-en.md)**
- 📕 **[《第一卷：破雾与筑基篇 (第 1~5 章)》](./docs/zh/01-Guide-Part1-Foundations.md)**
- 📗 **[《第二卷：空间状态与流程质量篇 (第 6~11 章)》](./docs/zh/02-Guide-Part2-State-and-Quality.md)**
- 📘 **[《第三卷：安全韧性演进篇与实战附录 (第 12~14 章 + 附录)》](./docs/zh/03-Guide-Part3-Security-and-Evolution.md)**

## 📜 开源协议
MIT License © 2026 **曾威长/Over9rowth**
