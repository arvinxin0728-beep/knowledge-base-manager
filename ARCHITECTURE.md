# Architecture（架构手册）
> 面向产出的研究型知识管理系统 — 当前结构、目标架构与渐进式迁移契约

---

## v0.8 研究员组合边界

共享包采用一个模块化单体内核。研究员身份、研究范围、知识来源、研究过程、研究输出、能力和治理是相互独立的维度；可选 preset 只提供可覆盖的默认值。解析器把这些维度合成为依赖有序的能力执行合同。

研究员工作区独占自己的来源、状态、运行命名空间、连接配置、企业知识和输出。共享包可以声明视频、钉钉、飞书等通用适配器接口，但不得包含实例化 MCP 配置、凭证、租户/节点标识、私人路径、企业分类或企业内容。就绪诊断只返回状态、原因和缺失字段名。

旧配置、`knowledge|video` profile 和 `--type` 保持兼容，但旧类型仅作为弃用别名映射到 preset。新增来源、过程、输出和能力必须扩展对应共享合同，不能复制内核。

---

## 一、业务架构

### 核心模型：五层知识管线

原文库（Source Libraries: ebooks, public accounts, articles） → 10-来源精炼（逐篇精炼笔记, Gate-10 quality gate） → 20-主题页（语义聚类, 推广评分 5 维度） → 30-可复用资产（Methods, Cases, Expressions, Frameworks） → 40-输出（费曼解释, 文章草稿, 方案材料, 决策备忘录）

**价值流：** 原始材料（大量、混乱、未结构化） → 阅读 + 精炼 → 单篇理解（结构化笔记，事实标记） → 聚类 + 推广评分 → 主题判断（综合多源，有明确问题） → 资产提取 → 可复用构件（方法、案例、表达、框架） → 组装 → 对外产出（面向读者的知识产品）

### 用户工作流

1. 新增来源到原文库（电子书 / 公众号 / 文章 / 网页）
2. 运行管线：`kb_pipeline.py discover → extract → claim → submit → commit`
3. Gate-10 检查精炼质量（结构完整性、内容 integrity、批次重复率）
4. `kb_manager.py promote` 做主题聚类与 5 维度评分
5. 评分 ≥ 4 的簇创建主题页
6. 提取可复用资产（方法、案例、表达、框架）
7. 组装对外产出（费曼解释、文章草稿、方案材料）
8. 整体门禁 quality-gate 验证关系完整性、可移植性、输出质量、事实验证

### 角色与边界

| 角色 | 职责 | 工具 |
|---|---|---|
| **人（知识工作者）** | 收集来源、审核推广、验证事实、决策产出 | 整理源文件、审核 promotion-review.md、运行 verify-claim |
| **Codex（AI 代理）** | 阅读精炼、主题合成、资产提取、输出起草 | SKILL.md 入口 + references/ 指令集 |
| **确定性脚本** | 目录初始化、索引管理、聚类打分、质量检查 | kb_manager.py、kb_pipeline.py、obsidian_linker.py |

---

## 二、系统架构

### 当前结构判断

当前版本具有清楚的业务价值流和文档分层，但代码仍是正在增长的单体：

- `SKILL.md` 同时承担意图路由、流程说明、质量规则、命令手册和发布规范。
- `scripts/kb_manager.py` 同时承担配置、持久化、审核、推广、治理、发布检查和 CLI 注册。
- `scripts/kb_pipeline.py` 同时承担运行时存储、事务状态机、提取、质量门调用和迁移。
- references 已按场景拆分，但尚未全部映射到稳定的代码能力模块。

因此目标不是拆成微服务，而是把现有系统演进为一个有明确边界的模块化单体。

### 目标模块

| 模块 | 高内聚职责 | 不应负责 |
|---|---|---|
| Intake | 来源发现、格式识别、提取、可读性 | 主题推广、发布 |
| Refinement | 阅读协议、精炼结构、Gate-10 | 来源扫描、生命周期治理 |
| Synthesis | 聚类、推广、主题综合 | 文件系统细节、发布排版 |
| Assets | 资产候选、资产生成、组合平衡 | 来源提取、运行时状态 |
| Publication | 输出生成、编辑成熟度、发布交接 | 来源发现、数据库管理 |
| Governance | 验证、生命周期、健康、质量门 | 具体内容生成 |
| Platform | 配置、路径、持久化、备份、Obsidian适配 | 领域判断 |

### 目标代码结构

```text
kbm/
├── domain/          # 稳定记录、枚举和领域规则；不依赖外层
├── application/     # Intake/Refinement/Synthesis/Assets/Publication/Governance 用例
├── infrastructure/  # 文件、SQLite、配置、Obsidian 等适配器
└── interfaces/cli/  # 参数解析和结果序列化

scripts/             # 保留旧命令名称的兼容入口
```

依赖方向固定为：`interfaces → application → domain`，基础设施通过应用层定义的接口接入。领域层不得依赖 CLI、用户目录、Obsidian 或 SQLite。

第一批公共内核已经落地：

```text
kbm/
├── domain/researcher.py   # 研究员身份与隔离契约
└── platform/
    ├── config.py          # 配置默认值、加载与验证
    ├── paths.py           # 研究员范围内的知识库、系统与运行时路径
    └── storage.py         # 备份轮转与操作日志
```

v0.6 增加研究员控制面：`kbm/application/researcher_registry.py` 负责注册、选择、冲突检查和健康诊断，`scripts/kb_researcher.py` 只负责 CLI 编排。注册表不承载任何研究内容、运行任务或共享 SQLite 状态。

v0.7 开始按职责抽离遗留管理单体。第一批将发布包扫描、README 新鲜度和发布哈希迁入 `kbm/application/package_release.py`，旧 `package-lint` CLI 保持兼容；`kb_manager.py` 的行数棘轮同步从 4275 下调到 4210，禁止迁出的代码重新回流。

v0.7.1 将 Markdown 文件收集、frontmatter、二级章节、标题和 wikilink 解析迁入无工作区依赖的 `kbm/domain/markdown.py`。它是 Gate-10、关系治理和新来源适配器的共享领域基础；主脚本棘轮进一步下调到 4145 行。

v0.7.2 将单篇来源精炼检查、批次模型文本重复检测和 Gate-10 报告渲染迁入 `kbm/application/refinement_quality.py`。旧 CLI 和 Pipeline 继续调用相同契约，主脚本棘轮降到 3835 行。

v0.7.3 将规则加载、来源匹配、主题聚类、五维评分、晋升原因、候选资产判断和三类评审渲染迁入 `kbm/application/promotion.py`；便携文件名规则迁入 `kbm/domain/naming.py`。主脚本棘轮降到 3605 行。

v0.7.4 将晋升决策账本、断点状态和安全 stub 迁入 `kbm/application/promotion_runtime.py`，并把共享时钟与 JSONL 持久化迁入 `kbm/platform`。主脚本棘轮降到 3350 行。

v0.7.5 将来源渠道、证据模式、时效敏感度、A-D 权重、风险信号、验证队列和陈旧结果检测迁入 `kbm/application/source_verification.py`；共享日期解析迁入 platform。主脚本棘轮降到 2975 行。

旧配置在内存中映射为隐式研究员，不强制迁移配置文件；新建配置写入显式研究员身份和运行命名空间。现有配置继续使用历史名称派生运行目录，避免数据库路径静默变化；新配置使用研究员 ID 作为命名空间。知识库路径身份始终参与计算，避免多个工作区共享 SQLite 或缓存。

### 渐进式迁移原则

1. 不重写现有系统，不改变已有 CLI 名称和 JSON 输出契约。
2. 先建立特征测试和架构棘轮，再逐个抽离模块。
3. 优先抽离配置、路径、原子写入、备份和标准记录等公共内核。
4. 每完成一次抽离，就下调 `architecture-contract.json` 中对应单体的复杂度上限。
5. 旧脚本最终只保留参数解析、兼容转换和应用用例调用。

### 自动架构门禁

`architecture-contract.json` 同时记录当前允许上限和目标值。当前上限是防止继续恶化的棘轮，不代表理想状态。

```bash
python3 scripts/architecture_check.py --strict
```

该检查阻断：入口文件继续越过复杂度预算、旧 CLI 命令意外消失、脚本间出现未经声明的新依赖。超过目标但尚未超过当前棘轮的项目以技术债警告呈现。

### 组件栈

指令层（Skill Layer — SKILL.md + references/） → 指导 → 脚本层（Script Layer — kb_manager.py + kb_pipeline.py + obsidian_linker.py + ebook_probe.py） → 读写 → 存储层（Storage Layer — 00-system/ + 10-/ + 20-/ + 30-/ + 40-/） ←→ 质量层（Quality Layer — Gate-10 + Quality-Gate + Verification-Queue + Output-Review + Package-Lint）

### 00-system/ 目录结构

active/（当前工作状态，不可重新生成）：
 processed-index.jsonl、run-log.jsonl、active-run-state.json、promotion-decision.jsonl、verification-queue.jsonl、verification-results.jsonl、output-review-results.jsonl、rules.md、topics.md

reports/（可重新生成的快照）：
 topic-clusters.md、promotion-review.md、asset-output-candidates.md、quality-gate.md、gate-10.md、verification-status.md、output-quality-review.md、output-review-status.md、portability-audit.md、topic-page-audit.md、relation-audit.md、asset-relation-audit.md、inbox-review.md

backups/（自动备份，保留最近 5 份，超出轮转）：
 processed-index.jsonl.*、quality-gate.md.* 等

### 质量门禁管线

管线流程：discover（发现） → extract（提取） → claim（认领） → submit（提交, Gate-10 检查） → commit-ready（提交就绪）

推广审核：promote（聚类推广, 5 分制） → 人工审批 → 创建主题页 → 资产矩阵判断 → 可复用资产 → 组装 → 最终产出

最终门禁：事实验证（verification passed?） → 输出评审（output review passed?） → 整体门禁（quality-gate passed?） → 知识就绪

### 数据流

来源输入（文件扫描 + pipeline discover/extract） → 核心处理（精炼协议 + 聚类评分 + 资产矩阵） → 写入持久状态（processed-index + run-log + active-run-state + promotion-decision） + 生成快照报告（topic-clusters + promotion-review + asset-output-candidates + quality-gate + gate-10）

持久状态 → 回读至核心处理

---

## 三、评分模型

推广评分由 5 个独立维度构成，每个维度通过得 1 分，满分 5 分。

| 维度 | 手动配置簇 | 自动发现簇（v0.1.1 修复前） | 自动发现簇（v0.1.1） |
|---|---|---|---|
| **来源数** ≥ 下限 | ✅ | ✅ | ✅ |
| **问题清晰度** 有明确要回答的问题 | ✅（预配置 question） | ❌（被 auto_discovered 阻断） | ✅（来源数足够时自动推断） |
| **可复用性** 含可提取的方法/案例/框架 | ✅（预配置 asset_type） | ❌（asset_type 默认为 unclassified） | ✅（关键字匹配或大簇保底） |
| **输出意图** 有明确的输出方向 | ✅（预配置 output_type） | ❌（无 output_type） | ✅（关键字匹配或大簇保底） |
| **风险可控** 高风险有验证措施 | ✅（但逻辑有 bug，总是 1 分） | ✅（同样 bug） | ✅（修复：高风险必须显式声明 verification_required） |

修复前自动发现簇的有效维度只有 1/5（来源数），其余 1 分来自 risk_controlled 永远为 True 的逻辑 bug。

### 评分与动作对应

| 总分 | 动作 |
|---|---|
| 0-1 | candidate_only — 仅保持候选，不创建任何文件 |
| 2-3 | topic_page — 创建主题页 |
| 4 | topic_page_and_asset — 创建主题页 + 可复用资产 |
| 5 | topic_page_asset_output — 主题页 + 资产 + 输出（高风险簇降级为验证后再输出） |

---

## 四、关键设计决策

### 为什么五层而不是扁平标签？

知识管理的核心问题不是「记了什么」，而是「这些材料能回答什么问题、产出什么价值」。

每一层有明确的产出问题：
- 来源精炼 → 「这篇讲了什么？我信多少？」（事实标记、不确定标注）
- 主题页 → 「关于这个问题的当前判断是什么？」（综合多源、形成判断）
- 可复用资产 → 「有什么方法/案例/框架可以反复调用？」（脱离单篇来源）
- 输出 → 「谁能用这个知识、怎么用、用在什么场景？」

### 为什么 script-first，而不是纯 Codex 技能？

知识库的管理需要长期运营，不能绑定单一 AI 平台。kb_manager.py、kb_pipeline.py 是纯 Python 脚本，可以在任何平台运行。SKILL.md 是 Codex 的入口，但翻译的是对脚本的调用指令，不是唯一入口。纯命令行环境也能跑（python3 kb_manager.py gate-10 --config <cfg>）。

### 为什么严格区分通用方法与用户目录映射？

一个输出文档如果正文里全是 /Users/xxx/Desktop/ 的路径，换一个读者就毫无用处。

所有方法论输出统一使用语义层名：原文库、来源精炼、主题页、可复用资产、输出。用户的私有路径只出现在三类地方：00-system/kb-config.json 配置文件、文档末尾的 Implementation example 区块、README.md 安装说明。

### 为什么产出之前必须过质量门禁？

AI 生成的精炼笔记有三种常见失败模式：
- 模板填充 — 看起来写了，但核心观点全是通用套话，没读原文
- 事实污染 — 把没有依据的 claim 写进去，读者以为是真的
- 批量重复 — 同批次所有文章的可复用模型字段一模一样

Gate-10 的三大检查直接针对这三个问题：结构检查、内容完整性、批次重复率（>30% 整批阻断）。

---

## 五、相关文档

| 文件 | 用途 |
|---|---|
| SKILL.md | Codex 技能入口，定义所有命令、工作流和质量控制规则 |
| README.md | 中文用户手册，安装方式、第一次使用指引、质量边界说明 |
| references/pipeline.md | 管线状态模型：发现 → 提取 → 认领 → 提交 → 提交就绪 |
| references/reading-and-refinement.md | 阅读与精炼协议，含 Gate-10 深度要求 |
| references/setup-and-config.md | 配置架构和目录映射规则 |
| references/promotion-control-and-resume.md | 成本分档、审批门禁、检查点恢复协议 |
| references/asset-output-matrix.md | 资产和输出触发矩阵及质量标准 |
| references/verification.md | 高风险事实验证工作流 |
| CHANGELOG.md | 版本变更记录 |
| architecture-contract.json | 可执行的架构预算、CLI兼容契约、依赖白名单和目标模块 |
| scripts/architecture_check.py | 架构棘轮检查入口 |
