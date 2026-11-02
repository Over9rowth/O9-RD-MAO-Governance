# 📘 O9-RD-MAO-Governance
### 从零构建高可靠多智能体系统：软件工程治理与 Multi-Agent 编排 (MAO) 完全指南

<p align="left">
  <strong>🌐 Language / 语言切换：</strong>
  <a href="./README.md">🇨🇳 简体中文</a> | 
  <a href="./README_EN.md">🇬🇧 English Version</a>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/O9--RD--Next-V1.0-brightgreen.svg)](./00-O9-RD-Next-V1.0-完整规范与实战模板.md)
[![Author](https://img.shields.io/badge/Author-曾威长%2FOver9rowth-purple.svg)](https://github.com/Over9rowth)
[![Docs](https://img.shields.io/badge/Docs-中文%20%7C%20English-orange.svg)](./README_EN.md)

> **📌 项目简介 (About)**：从零构建高可靠多智能体系统（MAO）——融合软件工程治理思想（一源三轨、契约先行、黑盒先行、SHA-256 哈希防伪）的工业级 AI 研发工作流规范、完整理论蓝皮书与开箱即用定制 Meta-Prompt。  
> *(Industrial-grade Multi-Agent Orchestration Governance Framework & Complete Guide. Taming LLMs with Software Engineering discipline. 👉 **[Click here for English Documentation](./README_EN.md)**)*
>
> **🏷️ 核心标签 (Topics)**：`multi-agent-systems` · `agent-orchestration` · `software-engineering` · `ai-governance` · `llm-workflow` · `design-by-contract` · `black-box-testing` · `o9-rd`

---

## 🌟 为什么你需要这个仓库？

市面上大多数野生 Multi-Agent 框架本质上是“让几个 AI 在群里自由聊天写代码”，在真实工程中极易死于四大绝症：**需求脑补放大**、**商业互吹审不出 Bug**、**删测试/写 `TODO` 假代码作弊（Reward Hacking）** 以及 **并发覆盖与死循环烧钱**。

本项目将人类软件工业积攒了 50 年的 **软件工程治理思想（Software Engineering Governance）** 降维打击引入多智能体编排：通过 **100% 确定性的软件工程控制面**（有限状态机、防伪基线、权限沙箱、黑白盒分离），将 **非确定性的 AI 执行面** 关进制度的笼子里，实现高可靠、可追溯的自动化研发交付。

---

## 📂 仓库核心目录与阅读导航 (Chinese & English)

### 🇨🇳 中文版全集 (Chinese Edition)
| 序号 | 文件入口 | 定位与适用场景 |
| :--- | :--- | :--- |
| 🛠️ **00** | **[《O9-RD Next V1.0 完整规范与实战模板》](./00-O9-RD-Next-V1.0-完整规范与实战模板.md)** | **【实战宪法与工具箱】** 含精简版 G0~G7 主规范、开箱即用的“核心四件套”文件模板（JSON/YAML/MD）及四大角色唤醒口令。 |
| 📕 **01** | **[《第一卷：破雾与筑基篇 (第 1~5 章)》](./01-Part1-破雾与筑基篇(第1-5章).md)** | **【零基础入门】** 解剖 Agent 四大器官、5 种协作拓扑、野生群聊四大灾难，确立“确定性控制面 vs 非确定性执行面”分离哲学与六大工程支柱。 |
| 📗 **02** | **[《第二卷：空间状态与流程质量篇 (第 6~11 章)》](./02-Part2-空间状态与流程质量篇(第6-11章).md)** | **【核心机制深潜】** 详解上下文防污染、四步哈希冻结与外部签名、三态分离、并发文件写入锁、风险路由、三层契约、A/B/C 三视角盲评与“黑盒先行”铁律。 |
| 📘 **03** | **[《第三卷：安全韧性演进篇与实战附录 (第 12~14 章 + 附录)》](./03-Part3-安全韧性演进篇与实战附录(第12-14章+附录).md)** | **【高阶保障与全量字典】** 涵盖 E2 沙箱六项正反向探测、C0-C3 四级变更、80% 残血安全交接、双环成对度量、人工埋雷校准，以及核心术语速查词典与主流框架对比。 |
| 🤖 **04** | **[《程序员 MAO 工作流定制教练 · Meta-Prompt》](./04-程序员MAO工作流定制教练-MetaPrompt.md)** | **【一键量体裁衣】** 将此提示词直接喂给 Claude / GPT / DeepSeek，AI 将化身敏捷工程教练，通过 4 个简单问题为你量身裁剪最适合当前项目的极简多智能体工作流！ |

### 🇬🇧 英文版核心套件 (English Edition)
| No. | Document Link | Description |
| :--- | :--- | :--- |
| 🌐 **EN-Home** | **[English Overview & Architecture Guide (`README_EN.md`)](./README_EN.md)** | Full architectural overview, core pillars, and quick-start guide in English. |
| 🛠️ **EN-00** | **[O9-RD Next V1.0 Master Specification & 4-Artifact Templates](./en/00-O9-RD-Next-V1.0-Specification-and-Templates.md)** | Complete English SOP (G0-G7 gates, S/M/L routing, E2 sandboxing) + ready-to-use JSON/YAML/MD templates & Agent system prompts. |
| 🤖 **EN-04** | **[Agile MAO Workflow Customizer · Meta-Prompt (English)](./en/04-Agile-MAO-Coach-MetaPrompt-EN.md)** | Feed this Meta-Prompt to Claude/GPT to interactively tailor a lightweight Multi-Agent workflow for your specific tech stack. |

---

## 🏗️ O9-RD 核心架构全景图（一源、三轨、双环治理）

```mermaid
flowchart TD
    subgraph Loop1["内环：项目交付闭环 - Project Loop"]
        G0["<b>G0 立项与风险路由</b><br/>风险一票否决分流 S/M/L, 设预算硬线"] --> G05["<b>G0.5 需求双向确认</b><br/>主总监复述: 必须做 / 明确不做 / AC"]
        G05 --> G1["<b>G1 设计与三层契约</b><br/>数据Schema / 行为不变量 / 可测性契约"]
        G1 --> G2["<b>G2 独立盲评 · 三视角</b><br/>只读白名单包, A架构/B安全/C更简替代"]
        G2 --> G3["<b>G3 候选冻结与批准</b><br/>SHA-256锁死考卷, 外部独立签名"]
        G3 --> G4["<b>G4 隔离开发与反作弊</b><br/>写入域隔离, 脚本拦截TODO与假数据"]
        G4 --> G5["<b>G5 独立验证 · 黑盒先行</b><br/>先物理屏蔽源码黑盒测, 再白盒与Fuzzing"]
        G5 -->|"发现缺陷 (开发不可自关)"| G4
        G5 --> G6["<b>G6 技术验收与交叉复审</b><br/>全量RTM需求追踪对账, 抽查原始证据"]
        G6 --> G7["<b>G7 签收与发布分离</b><br/>站长分别决定: 签收、发布上线与归属"]
    end
    subgraph Loop2["外环：流程进化闭环 - Process Loop"]
        G7 --> O["运行观察与成对度量采集<br/>评审成立率vs漏报 / 门禁拦截四分类"]
        O --> P["SOP 规则校准与升级提案<br/>经站长批准后演进下一代工作流"]
        P -.-> G0
    end
```

---

## 📜 开源协议与版权署名 (License)

本项目采用 [MIT License](./LICENSE) 开源协议。  
Copyright © 2026 **曾威长/Over9rowth**. 欢迎自由阅读、引用、修改及在商业/个人项目中落地实践（请保留原作者 **曾威长/Over9rowth** 署名）。
