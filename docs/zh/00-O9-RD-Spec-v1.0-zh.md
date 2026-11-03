# 🛠️ O9-RD Next V1.6.4｜多智能体研发工作流完整规范与实战模板（架构师精简实战版）

> **版本定位**：本版由 V0.4 拟定稿经首席架构师工程化重构而成（V1.6.4 Production Ready）。  
> **核心改造**：  
> 1. **彻底践行“控制面与执行面分离”**：废除由 AI 担任的“资料管理员”，所有哈希计算、白名单打包、必填项校验、反作弊扫描均由底层确定性脚本（`gate_runner.py`）接管。  
> 2. **砍除 40% 官僚虚火**：废除动态角色资格池升降级、废除繁琐的人类阅读分钟数公式、废除 G2 转 G6 利益披露长文（改为强制新开纯净会话）。  
> 3. **工件大瘦身**：将原 20+ 个零散模板整合为**“核心四件套”**，大幅降低 Token 消耗与格式报错率。  
> 4. **100% 保留黄金骨架**：一源四轨、G0.5 双向确认、三层契约、G2 三视角盲评、G3 四步哈希冻结与外部签名、G4 写入域隔离与反作弊、G5 黑盒先行与强制 Fuzzing、C0-C3 四级变更、80% 残血安全交接、G7 签收发布分离。

---

# 第一部分：O9-RD 核心工作流主规范 (The Master SOP)

## 1. 核心铁律（不可裁剪的 10 条底线）
1. **一源（SSOT）**：同一时点只有一套有效执行基线。禁止靠聊天记录传话，一切交接以落盘文件为准；基线内部冲突时立即阻塞（Blocked），严禁 AI 自行猜测哪个文件优先。
2. **控制面代码化**：计算 SHA-256、追加事件时间戳、控制目录读写权限、扫描 `TODO` 假代码，必须由底层脚本或操作系统权限执行，严禁让大模型手填哈希或自证清白。
3. **G0.5 双向复述**：写任何设计或代码前，主总监必须先用大白话复述“做什么、明确不做什么、验收标准（AC）”，经站长（人类老板）明确确认后方可推进。
4. **契约先行**：G1 必须交付数据/接口定义、行为契约与可测性契约（`test-harness`）。无适用数据结构需显式声明 `no-applicable-data-contract`。
5. **不相容职责分离（SoD）**：同一变更的设计/开发者，绝不得担任该变更的 G2 独立评审者、G5 独立测试者或 G6 交叉复审者。
6. **G2 盲评与三视角**：评审者在纯净新会话中只读白名单资料包（初次提交前互不可见），每人必须覆盖 **A（架构与需求）、B（安全与可靠性）、C（更简替代方案）** 三个视角。
7. **G3 外部独立签名**：先锁死候选文件计算 SHA-256 清单摘要，再由外部独立的批准记录单向引用该摘要，严禁将批准状态写回被哈希文件造成循环依赖。
8. **G5 黑盒先行铁律**：独立测试者必须先在**物理屏蔽实现源码**的条件下完成黑盒用例设计与首轮行为验证并锁死记录，随后才可读取源码开展白盒检查与专项测试。开发不得自行关闭独立测试提出的 Bug。
9. **G7 签收与发布分离**：技术验收（G6）、站长签收、生产发布授权分别记录。批准开发（G3）或签收成果，绝不等于授权操作生产环境。
10. **诚实留痕**：沉默或超时绝不视为批准。AI 无法触达的硬件/真机场景必须生成《人工验证待办卡》并保持 `not-run/blocked`，严禁伪造测试日志或脑补 `passed`。

---

## 2. 角色职责与沙箱隔离标准

### 2.1 精简角色清单（5+1 架构）
| 角色 | 担任者 | 核心职责 | 绝对禁令 |
| :--- | :--- | :--- | :--- |
| **站长 (Owner)** | 人类老板 | 确认目标与路线、批基线、裁决争议、接受残余风险、签收与授权发布 | 不把未验证结果记为已验证 |
| **主总监 (Director)** | 主控 Agent | 澄清需求、编写契约方案、回应评审、拆解任务卡、集成与 G6 初验 | 严禁篡改评审原文、严禁偷扩授权、兼任开发时严禁自验通过 |
| **评审员 (Reviewer)** | 独立 Agent (新会话) | 在只读白名单内按 A/B/C 三视角提交可定位的评审发现 | 严禁改方案、严禁翻看未授权源码、严禁下发开发指令 |
| **开发员 (Coder)** | 执行 Agent (可并行) | 在授权路径域内写代码、跑自测、提交 Diff 与构建候选 (`candidate_id`) | 严禁偷改 AC 配合实现、严禁跨界改共享文件、严禁自关 Bug |
| **测试/复审员 (QA/Auditor)**| 独立 Agent (新会话) | G5 黑盒先行测试、Fuzzing、白盒检查、复测关单；G6 独立抽查证据 | 严禁参与被测代码编写、严禁先看源码倒推黑盒用例 |
| **看门狗 (`gate_runner`)**| **Python/Shell 脚本** | **算 SHA-256、打白名单包、追加事件、拦 `TODO`/Mock、卡状态机** | **严禁使用大模型扮演此角色** |

### 2.2 隔离等级（E0 ~ E2）与技术实现
*   **E0（口头承诺）**：仅靠 Prompt 叮嘱。不计入任何独立评审/测试最低要求。
*   **E1（受控新会话）**：开启全新 API Session，仅投喂静态白名单文件包，无历史上下文继承。适用于 S/M 轨。
*   **E2（技术沙箱隔离，L 轨强制）**：在 E1 基础上，通过容器只读挂载（Read-only Volume）或工具层代码硬拦截（`if path not in whitelist: raise PermissionError`），物理剥夺源码写权限、非白名单读权限与无关网络工具。
    *   *E2 最小核验六项（I-01~I-06）*：运行前由脚本自动执行一次**正向探测**（确认白名单可读、报告目录可写、测试命令可跑）与**反向探测**（故意读取一个已存在的非白名单无害样例文件，必须真实触发 `PermissionDenied` 日志，404 或超时不算）。

---

## 3. G0 风险一票否决路由与四轨机制（Trivial / S / M / L）

立项时按以下顺序漏斗式过滤，**严禁取平均分抵消高风险**（风险未知先标 `null` 做只读盘点，不得默认 `false`）：

### 3.1 第一步：查 L 轨高风险红线（命中任一强制走 L 轨）
1. 改变认证、授权、租户隔离、密钥管理或关键安全边界。
2. 新增/扩大敏感个人数据、凭据、核心内部数据的收集/导出，或隔离未经验证。
3. 不可逆删除/迁移、无法验证恢复的数据写入，或生产数据大范围变更。
4. 涉及资金流、计费结算、对外交易，或错误会造成重大现实损失。
5. 大范围生产基础设施、安全配置或关键服务变更。
6. 赋予 Agent 会产生外部副作用的新工具权限或自动授权边界。
7. 跨系统核心架构重构。

### 3.2 第二步：划分 M / S / Trivial 轨
*   🟡 **M 轨（标准敏捷轨）**：未命中 L 轨红线，但涉及新增业务行为、模块间接口定义、数据结构变更或外部集成。
*   🟢 **S 轨（轻量快速轨）**：必须同时满足——纯局部文案/样式/文档或孤立小修复 + 不改已批 AC 与公共接口 + 不改权限与生产配置 + 回退明确 + 已指定独立黑盒验证人。
    *   *S 轨“两次集中触点”*：**触点 1（开工前）** 站长一次回复同时完成立项、G0.5 确认与 G3 基线批准；**触点 2（交付后）** 站长一次回复同时完成 G6 外部证据核对与 G7 签收发布决定。
*   ⚪ **Trivial 轨（微调预授权通道）**：纯注释/README 文档修正、纯静态错别字微调（改动 < 20 行且不触碰任何逻辑、配置与依赖）。主总监改完展示 `git diff`，站长确认后直接合入，免除 G2/G5。

---

## 4. 状态机引擎与 9 个门禁节点操作细则（G0 / G0.5 / G1 ~ G7）

### 4.1 三类状态正交存储
在 `project_state.json` 中严格分开存储，防止状态欺骗：
*   `phase`: `G0 | G0.5 | G1 | G2 | G3 | G4 | G5 | G6 | G7 | observing | archived`
*   `execution_state`: `active | awaiting-approval | blocked | rework-required | paused | cancelled | completed`
*   `gate_results`: 每道门禁独立取 `not-started | in-progress | passed | conditional | failed | waived | not-applicable`

### 4.2 各门禁标准动作（Gate-by-Gate Protocol）

#### 【G0 立项】与【G0.5 需求双向确认】
1. 主总监建立项目状态账本，登记风险路由（S/M/L）、Token/费用预算上限（默认 **80% 预警、100% 硬停止**）及环境事实基线（OS、Shell、编码、工作目录）。
2. 主总监在 `spec_and_contracts.md` 中填写 G0.5 复述（区分：站长原话 / 总监推断 / 待验证假设），明确列出**必须做**、**明确不做**及结构化 **AC（含前置条件、输入、预期结果、核心/一般分级）**。
3. *技术未知实验出口（Spike）*：若技术可行性未知，申请小预算在隔离环境跑原型；实验结束后带着结论退回 G0.5，**实验代码严禁直接免检当正式代码交付**。
4. **出口**：站长明确回复确认复述内容。

#### 【G1 设计与三层契约】
主总监在 `spec_and_contracts.md`（及配套接口文件）中完成设计并交出三层契约：
1. **数据/接口契约**：OpenAPI / JSON Schema / TypeScript 类型等真实机器定义文件，由脚本跑通语法校验（无数据结构则声明 `no-applicable-data-contract`）。
2. **行为契约**：状态转换、异常返回码、业务不变量（Invariants）。
3. **可测性契约（Test Harness）**：明确测试启动命令、就绪判断条件（Readiness）、测试库重置命令（严禁指向生产库！）、外部依赖 Mock 方式、日志位置与清理步骤。L 轨额外填写 **Fuzzing 输入面与预算计划**。

#### 【G2 独立三视角盲评】（S 轨可按条件豁免，M 轨 $\ge 1$ 人，L 轨 $\ge 2$ 人且优先异构模型家族）
1. `gate_runner` 脚本打包白名单只读材料（含脱敏副本、需求与契约），**剔除主总监自评与其他评审员意见**。
2. 评审员在纯净新会话中输出 A（架构与需求）、B（安全与可靠性）、C（创新与更简替代路线）三视角报告，每条发现标记 `Blocker | Major | Suggestion`（或 `No finding | Insufficient evidence`）。
3. 原始报告封存。主总监在 `review_and_defects.yaml` 逐条回复（`采纳 | 部分采纳 | 不采纳 | 待澄清`）。脚本校验原始 ID 与回复 ID 100% 映射无遗漏。
4. **出口**：所有 `Blocker` 已修订消解（或经客观证据证实误报并经独立核对）。若总监与评审员争执不下，最多往返 **2 轮** 立即升级呈交站长裁决。

#### 【G3 候选冻结与站长授权】（四步防伪冻结法）
1. 主总监完成契约与方案修订，停止文件修改。
2. `gate_runner` 脚本计算 `spec_and_contracts.md` 及接口契约文件的字节级 SHA-256，生成冻结清单 `manifest`，并算出 `manifest_sha256` 总指纹。
3. 向站长呈交一页纸决策摘要（含改动点、争议项、权限范围与 `manifest_sha256`）。
4. **出口**：站长回复批准后，脚本在外部 `o9_workspace/approvals.jsonl` 独立追加账本中写入批准记录并绑定该 `manifest_sha256`。此后任何针对基线文件的字节改动均触发脚本报警熔断。

> **V1.6.4 控制面落地说明**：`gate_runner.py` 在冻结前强制校验 `spec_and_contracts.md` 非空且含结构化 `AC-xxx` 表行（G1-01）；`manifest` 覆盖 `spec_and_contracts.md` 与 `o9_workspace/contracts/**` 下的全部契约文件，复合指纹 `manifest_sha256` 连同 `files[]` 清单一并签入 FREEZE 记录，`approve` 与 `check` 均重算并比对（G3-01/G3-02）。本地 `.o9_project_id` 与 `~/.o9-trust/index.tsv` 注册表钉死工作区与项目绑定，并提供 `trust-reset <PROJECT_ID>` 灾后恢复通道（G3-03）。G5 阶段要求 `evidence_log_ref` 落在仓库根目录之内且非空，最新一次 QA 运行按 `recorded_at` 时序选取，缺陷与运行条目支持任意键序解析（G5-02/G5-03）。

#### 【G4 隔离开发、并发控制与反作弊检查】
1. **文件写入域（Write Scope）隔离**：并行任务卡必须声明 `allowed_write_paths`。同一工作区并发任务的写入路径严禁重叠！公共文件（如依赖配置、共享类型）指定唯一当期持有者串行修改。
2. **反作弊扫描（Anti-Stubbing）**：开发自测完成后，`gate_runner` 自动扫描代码差异：
   * 拦截生产路径下的未完成占位符（`TODO`、`FIXME`、空函数、`pass`）；
   * 核对《测试替身与演示数据清单》，严禁 Mock 数据、硬编码假返回值流入正式生产可达路径；
   * 拦截删除断言或永真断言（`assert True`）。
3. **确定性错误熔断**：同一命令报错且代码/环境无实质变化时，严禁原样盲目重试。
4. **出口**：构建生成唯一候选版本标识 `candidate_id`（锁定源码 Commit、依赖锁与配置摘要），移交 G5。

#### 【G5 独立验证：黑盒先行、Fuzzing 与缺陷闭环】
1. **阶段一：蒙眼黑盒测试（Black-box First）**
   * 启动全新测试会话，**物理屏蔽业务实现源码**，仅投喂获批需求、AC、行为/可测性契约及构建好的 `candidate_id` 测试入口。
   * 测试员先冻结首轮黑盒用例，执行正常、边界、异常与权限测试，生成不可覆盖的运行记录（含命令、退出码、实际观察与日志路径）。
2. **阶段二：L 轨强制 Fuzzing 与睁眼白盒测试**
   * 首轮黑盒结论锁死后，开放源码只读权限，开展白盒检查（异常分支、并发、资源释放、Agent 提示词注入与工具越权）。
   * L 轨强制按计划运行 Fuzzing（模糊测试），不仅检查是否崩溃（Crash），必须核对是否破坏业务不变量与数据完整性。
3. **阶段三：AI 无法触达的场景 $\rightarrow$ 《人工验证待办卡》**
   * 需真机硬件或人工体验的 AC，状态保持 `not-run` 或 `blocked`，生成待办卡交人类实测后回填，严禁 AI 猜测填 `passed`。
4. **缺陷闭环铁律**：Bug 状态流转 `open -> fixing -> ready-for-retest -> closed`。开发员修完只能标 `ready-for-retest` 并生成新 `candidate_id`；**唯有独立测试员复测通过并跑完受影响回归后，才有权将 Bug 改为 `closed`**。

#### 【G6 技术总验收与 RTM 对账】
1. 在 `rtm_acceptance.md` 中拉出全量获批 AC，逐行对齐：对应代码提交、测试用例 ID、运行记录 `run_id`、覆盖状态（`covered`）与测试结果（`passed`）。
2. **独立复核要求**：
   * 若主总监兼任了开发，S/M 轨必须由站长或未参与开发的独立会话核对测试运行证据；
   * L 轨无论是否兼任，强制启动一个全新的 **G6 交叉复审会话**，抽查关键 AC 原始日志、专项证据及未关闭项。
3. **条件通过（Conditional）**：非阻塞瑕疵（Major/Suggestion）如需带病放行，必须登记条件台账（明确限制措施、责任人、截止期与逾期停用动作）。**Blocker 及核心 AC 失败严禁办条件通过！**

#### 【G7 站长签收、发布分离与双环复盘】
1. 站长在 `rtm_acceptance.md` 末尾分别做出三项独立决定：① **是否签收成果**；② **是否及何时授权发布上线**；③ **项目归属与开源许可证（License）决定**。
2. 获批发布后，按发布包执行部署与冒烟检查（Smoke Test）。
3. 采集最小度量数据（Token/费用、打回次数、门禁拦截四分类归因、逃逸缺陷），按成对指标复盘并决定是否升级 SOP。

---

## 5. 异常治理：变更控制（C0-C3）、残血交接与紧急热修

### 5.1 开发期四级变更控制
*   **C0（实现内微调）**：不改 AC、不改接口契约、不改安全边界 $\rightarrow$ 任务内记录差异并跑测试，无需请示。
*   **C1（兼容契约扩展）**：原需求范围内兼容扩展且风险不增（需核对严格校验消费者，不能仅凭“新增可选字段”断定兼容） $\rightarrow$ 有站长预授权则由总监核验登记派生基线；无预授权报站长快批。
*   **C2（局部破坏/标准变更）**：接口不兼容或 AC 改变 $\rightarrow$ **立即暂停受影响范围**，定向复审并由站长重批 G3 基线。
*   **C3（需求/安全重大推翻）**：核心目标改变或触发高风险升档 $\rightarrow$ **全线停止**，退回 G0/G0.5/G1 重新路由。

### 5.2 预算预警与“残血安全交接（Handoff）”
*   当资源消耗达 **80% 预警线**，停止开启新任务，使用预留的 20% **收尾资源（Closing Reserve）** 在安全点保存**工作快照（Work Snapshot）**。
*   **快照保真铁律**：如实记录未提交代码（`git diff`）、未跑检查与未知副作用；**严禁为追求“干净快照”擅自回滚删除用户半成品代码，也严禁将工作快照谎称为获批基线！**
*   突发断电/额度秒空允许记为 `handoff.status: incomplete`；接替者须等原写入锁释放并核验磁盘现场一致后，方可恢复写入。

### 5.3 紧急热修（Hotfix）
仅用于线上真实故障止损。在预授权范围内先执行回滚/关停/最小修复；若现场无条件跑完整 G5，如实标为**“受限应急处置”**（禁伪造 G5 通过记录），系统稳定后 **24 小时内** 补齐热修卡、独立复测与根因复盘。

---
---

# 第二部分：O9-RD 开箱即用“核心四件套”文件模板

> **使用方法**：新建项目时，在项目根目录创建 `o9_workspace/` 文件夹，初始化以下 4 个核心文件即可承载全部治理数据：

```text
o9_workspace/
 ├── project_state.json         # 【核心件 1】控制面状态机、当前生效基线元数据与审计事件缓存
 ├── spec_and_contracts.md      # 【核心件 2】G0.5 双向确认 + AC 标准 + G1 三层工程契约主考卷
 ├── review_and_defects.yaml    # 【核心件 3】G2 三视角盲评处置 + Mock 清单 + G5 测试运行与缺陷台账
 ├── rtm_acceptance.md          # 【核心件 4】G6 全量需求追踪矩阵 (RTM) + 条件台账 + G7 站长三项决定
 └── approvals.jsonl            # 【独立账本】只读追加签名账本（配合 ~/.o9-trust/ 外部锚点与 HMAC-SHA256 哈希链）
```

> **账本解耦与默认红灯声明**：除核心四件套外，`init` 还会初始化只读的独立追加签名账本 **`o9_workspace/approvals.jsonl`**（配合 `~/.o9-trust/` 外部锚点与 HMAC-SHA256 哈希链），彻底将批准签名与 `project_state.json` 状态缓存分离，消除自哈希循环依赖。所有出厂模板均为**默认红灯状态（Default-Red）**：黑盒测试未通过（`source_code_hidden_verified: false`、`exit_code: -1`、含 `recorded_at` 时间戳）、缺陷关闭状态仅限 `closed / verified`、AC 追踪默认为 `not-covered / not-run`、G7 签收默认为 `pending`，严禁零工作量直接通关。

---

## 模板 1：`project_state.json`（控制面状态机、当前生效基线元数据与审计事件缓存）
*(注：本文件由 `gate_runner.py` 维护；批准签名独立存于只读追加账本 `o9_workspace/approvals.jsonl` 中)*

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

## 模板 2：`spec_and_contracts.md`（G0.5 双向确认 + AC 标准 + G1 三层工程契约主考卷）

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

## 模板 3：`review_and_defects.yaml`（G2 三视角盲评处置 + Mock 清单 + G5 测试运行与缺陷台账）

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

## 模板 4：`rtm_acceptance.md`（G6 全量需求追踪矩阵 (RTM) + 条件台账 + G7 站长三项决定）

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

## 附：日常角色启动极简口令卡（供复制粘贴给各 AI 会话）

### 1. 唤醒【主总监 Agent】口令
> “你现在担任本项目的 **O9-RD 主总监（Director）**。请读取 `o9_workspace/project_state.json` 和 `spec_and_contracts.md`。  
> **你的铁律**：在 G0.5 未获我（站长）明确确认前，严禁编写具体业务代码！请先对我的需求进行风险路由判定（S/M/L），并输出《G0.5 双向确认单》（我理解的目标、必须做、明确不做、AC 列表）供我审阅。”

### 2. 唤醒【G2 独立盲评 Agent】（新开纯净会话）口令
> “你现在担任 **O9-RD G2 独立评审员**。你处于无历史上下文的独立盲评会话中。请仅读取我发给你的 `spec_and_contracts.md`。  
> **你的铁律**：严禁索要未授权仓库代码，严禁客套吹捧。请严格从 **视角A（架构与需求吻合度）、视角B（安全与可靠性边界）、视角C（是否存在更简单的替代方案）** 三个维度进行挑刺，按 `Blocker / Major / Suggestion` 输出结构化发现及验证方法。”

### 3. 唤醒【G4 开发员 Agent】口令
> “你现在担任 **O9-RD G4 开发执行者**。请读取已冻结的 `spec_and_contracts.md`。  
> **你的铁律**：1. 严格限制在授权路径 `[填入路径]` 内修改代码，严禁触碰共享核心文件与需求基线文档；2. 严禁使用 `TODO`、硬编码假数据或测试替身（Mock）冒充正式生产实现；3. 严禁修改或删除验收标准（AC）。完成后请运行自测并汇报构建候选号 `candidate_id` 及实际运行输出。”

### 4. 唤醒【G5 独立黑盒测试 Agent】（新开纯净会话）口令
> “你现在担任 **O9-RD G5 独立验证测试员**。  
> **你的最高铁律（黑盒先行）**：在第一阶段，**严禁读取任何业务实现源代码（`src/`）**！你只能根据 `spec_and_contracts.md` 中的 AC 和 §2.4 可测性契约（Test Harness），设计黑盒测试用例并针对候选程序执行测试。请如实记录运行命令、退出码与实际观察结果。对于你无法触达的硬件/真机体验项，必须标记为 `not-run` 并生成《人工验证待办卡》，严禁猜测填写 `passed`！只有在我确认你的首轮黑盒结果已锁死落盘后，你才能申请读取源码开展第二阶段白盒检查。”