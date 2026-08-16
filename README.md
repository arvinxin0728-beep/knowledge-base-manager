# Knowledge Base Manager 中文说明

当前版本：`v0.7.7`

当前开发线：`v0.8.0` 架构收敛。保持现有命令和配置兼容，将主脚本中的高内聚能力逐步迁移到独立应用模块；迁移本身不改变知识库目录、运行状态或正式知识资产。证据接入、来源索引规范化、输出机械质量评价和编辑质量评分已经迁移为独立应用模块，并保留旧 CLI 入口。

研究员初始化支持可组合类型预览：研究员类型定义任务与默认输出，能力目录定义来源、研究、资产、输出和集成能力。旧 `--profile knowledge|video` 保持兼容；新初始化可先运行 `kb_researcher.py types`、`capabilities` 和 `plan-init`，确认解析后的能力、依赖及尚未安装的适配器后再执行 `init --type ...`。

企业连接遵循实例隔离边界：主技能只声明通用钉钉、飞书等连接能力；真实 MCP 配置、凭证、节点 ID、企业知识和资料只能保存在对应研究员实例中。发布检查会阻断私有路径和嵌入式连接配置，研究员 `doctor` 会拒绝明文凭证。

许可证：MIT

发布状态：Beta。适合试用、评估和小规模真实知识库验证；不应包装成完全成熟的零配置产品。

## 这是什么

`knowledge-base-manager` 是一个面向产出的研究型知识管理系统，也是一套可初始化多个独立研究员的研究员系统能力。

它不是单纯的“文章总结工具”，也不是把资料搬进一个文件夹的自动化脚本。它的目标是把电子书、公众号文章、网页文章、报告、笔记等原始材料，逐步处理成可理解、可关联、可复用、可输出的研究资产。

在新定位下，一个“研究员”是一个独立配置的研究单元：它有自己的资料输入、研究过程、知识库、质量门禁和输出。一个电脑可以安装并运行多个研究员，不同研究员分别研究不同主题或项目；它们的知识输入、过程状态和输出默认相互隔离，但研究方法、评审标准、补证流程、模板和经过验证的闭环经验可以相互学习、抽象后共享。

它最初以 Codex skill 的形式实现，但底层模型和脚本不绑定 Codex。其他 Agent 平台也可以把它作为“指令包 + 本地脚本工具包”使用。

系统的核心判断是：

> 原文库不是知识库。真正的知识库应该存放已经被读懂、压缩、结构化、可复用的内容。

## 它解决什么问题

很多个人知识库最后会失败，常见原因不是收集太少，而是收集太多：

- 原文越来越多，但没有被真正阅读和吸收
- 摘要越来越多，但无法形成主题判断
- 标签和双链很多，但不知道什么内容可以复用
- 知识库看起来很丰富，但写文章、做方案、讲课、决策时用不上

这个系统试图解决的问题是：如何让知识从“收集”逐步晋升为“研究能力”和“产出能力”。

## 核心模型

系统的最小运行单位是“研究员”。每个研究员分成两大区域：

1. 原文库：存放用户提供的电子书、文章、公众号导出、网页剪藏、报告等原始材料。
2. AI 知识库：存放被读懂、压缩、结构化、可复用后的研究内容。

`10-source-refinements` 不是原文库，而是原文被阅读后的第一层处理结果。每一条来源精炼都必须能追溯到该研究员 `source_libraries` 中的原始材料。

单研究员的默认完整结构是：

```text
Knowledge-System/
├── Sources/                         # 原文库，不放 AI 精炼结果
│   ├── Ebooks/                      # 电子书、PDF、EPUB、DOCX 等
│   ├── Articles/                    # 网页文章、剪藏、普通文章
│   └── Public-Accounts/             # 公众号文章导出或同步结果
└── AI-Knowledge-Base/               # AI 知识库，不存原文
    ├── 00-system/                   # 系统配置、索引、运行记录、评审记录
    ├── 10-source-refinements/       # 来源精炼：对单篇文章、单本书、单份资料的结构化阅读
    ├── 20-topic-pages/              # 主题页：把多个来源合成为一个问题的阶段性答案
    ├── 30-reusable-assets/          # 可复用资产：方法论、案例、表达、框架、清单等
    └── 40-outputs/                  # 输出：费曼解释、文章草稿、方案素材、决策备忘、复盘记录等
```

这五层不是文件夹命名要求，而是通用知识流转模型。不同用户可以把它映射到自己的目录结构里。

多研究员的推荐结构是：

```text
Research-System/
├── shared-methods/                  # 可共享的方法、rubric、模板、闭环经验
├── researchers/
│   ├── ai-knowledge-researcher/      # 研究员 A：独立输入、过程和输出
│   │   ├── Sources/
│   │   └── AI-Knowledge-Base/
│   └── sales-researcher/             # 研究员 B：独立输入、过程和输出
│       ├── Sources/
│       └── AI-Knowledge-Base/
└── registry/
    └── researchers.json              # 研究员发现登记，不存放共享运行状态
```

原则是：技能和方法可以共享，研究记忆默认隔离。一个研究员的结论不能悄悄变成另一个研究员的事实依据；如果需要跨研究员引用，必须显式导入、标注来源，并按证据层级处理。

研究员控制面使用独立脚本，避免继续扩张知识处理主脚本：

```bash
python3 scripts/kb_researcher.py registry-init --registry <researchers.json> --apply
python3 scripts/kb_researcher.py register --registry <researchers.json> --config <kb-config.json> --apply
python3 scripts/kb_researcher.py list --registry <researchers.json>
python3 scripts/kb_researcher.py select --registry <researchers.json> --researcher-id <id> --apply
python3 scripts/kb_researcher.py doctor --registry <researchers.json>
```

注册表只用于发现和选择研究员，不保存共享任务状态。视频 profile 可以初始化视频输入、转录文本和关键帧目录，但在视频适配器实现前会明确标记为 `adapter_not_installed`，不能据此宣称视频采集和转录已经可运行。

例如，一个用户可以使用中文目录：

```text
知识系统/
├── 800-电子书库/                 # 原文库：电子书
├── 801-公众号库/                 # 原文库：公众号文章
└── 888-AI知识库/                 # AI 知识库：处理后的知识
    ├── 00-系统/
    ├── 10-来源精炼/
    ├── 20-主题页/
    ├── 30-可复用资产/
    └── 40-输出/
```

另一个用户也可以使用英文目录、Obsidian vault、项目资料夹，或者其他命名方式。目录名只是实现映射，不是方法本身。

配置文件通过 `source_libraries` 指定原文库位置，例如：

```json
{
  "name": "my-researcher",
  "researcher": {
    "id": "my-researcher",
    "name": "My Researcher",
    "domain": "研究主题或项目范围",
    "role": "researcher",
    "isolation": "independent_workspace",
    "shared_methods": []
  },
  "source_libraries": {
    "ebooks": "/absolute/path/to/Sources/Ebooks",
    "articles": "/absolute/path/to/Sources/Articles",
    "public_accounts": "/absolute/path/to/Sources/Public-Accounts"
  },
  "ai_knowledge_base": "/absolute/path/to/AI-Knowledge-Base"
}
```

## 每一层放什么

### 00-system

放系统运行需要的配置、索引、操作日志和质量控制文件。按类型分为三个子目录：

- `active/` — 当前工作状态，不可重新生成
- `reports/` — 快照报告，可被 `--apply` 重新生成覆盖
- `backups/` — 自动备份（保留最近 5 份，超出自动轮转）

常见内容包括：

`active/`：
- `processed-index.jsonl`：已处理来源索引
- `run-log.jsonl`：操作日志（每次 `--apply` 追加一条结构化记录）
- `active-run-state.json`：中断和恢复状态
- `promotion-decision.jsonl`：晋升决策记录
- `verification-queue.jsonl`：待验证事实队列
- `verification-results.jsonl`：验证结果

`reports/`：
- `topic-clusters.md`：主题候选聚类
- `promotion-review.md`：晋升评审记录
- `asset-output-candidates.md`：资产和输出候选
- `quality-gate.md`：质量管理综合门禁
- `gate-10.md`：精炼层质量门禁结果（结构 + 内容 + 批次检查）
- `lifecycle-audit.md`：晋升后知识的生命周期、回退和降级建议
- `knowledge-health.md`：正式知识的定期健康度复审结果

这一层主要给系统和操作者看，不是正式知识内容。

### 新鲜度文件名规则

正式知识内容，也就是 `10-source-refinements`、`20-topic-pages`、`30-reusable-assets`、`40-outputs` 中的 Markdown 文件，需要在文件名暴露知识新鲜度。

`10-source-refinements` 采用三日期：

```text
YYYY-MM-DD YYYY-MM-DD YYYY-MM-DD Title.md
```

依次对应：`updated_at`、`created_at`、`saved_at`。

其中 `saved_at` 表示原始材料进入来源库/原始材料库的日期，不是发布日期、处理日期，也不是精炼文件创建日期。历史文件缺失 `saved_at` 时，只能优先从 `source_file` 指向的原始文件名前缀日期恢复；无法恢复时应进入人工复核，不能静默用 `created_at` 或 `processed_at` 代替。

`20-topic-pages`、`30-reusable-assets`、`40-outputs` 采用两日期：

```text
YYYY-MM-DD YYYY-MM-DD Title.md
```

依次对应：`updated_at`、`created_at`。当正文、frontmatter、关系链接或知识判断更新时，必须同步更新 `updated_at` 和文件名第一日期。

常用命令：

```bash
python3 scripts/kb_manager.py audit-filename-dates --config <config>
python3 scripts/kb_manager.py normalize-filename-dates --config <config> --apply
python3 scripts/kb_manager.py normalize-filename-dates --config <config> --touch-updated-at --apply
python3 scripts/kb_manager.py audit-source-quality --config <config> --apply
python3 scripts/kb_manager.py audit-evidence-gaps --config <config> --apply
python3 scripts/kb_manager.py init-evidence-intake --config <config> --apply
python3 scripts/kb_manager.py audit-evidence-intake --config <config> --apply
python3 scripts/kb_manager.py audit-editorial-quality --config <config> --apply
python3 scripts/kb_manager.py audit-lifecycle --config <config> --apply
python3 scripts/kb_manager.py audit-knowledge-health --config <config> --apply
python3 scripts/kb_manager.py init-lifecycle-health --config <config> --apply
```

`quality-gate --strict` 会阻塞缺失新鲜度文件名、文件名日期与 frontmatter 不一致，或 `updated_at < created_at` 的情况。生命周期和健康度问题默认作为 warning 暴露，先给出回退、修订、补证据、复审或归档建议，不自动移动或删除知识。`init-lifecycle-health --apply` 用于初始化旧知识的治理字段；它会把健康状态设为 `review_due`，而不是直接假定为 `healthy`。

### 10-source-refinements

放单个来源的精炼结果。

每个文件通常对应一篇公众号文章、一本书、一个网页、一次访谈或一份报告。它回答的是：

- 这份材料讲了什么问题？
- 核心观点是什么？
- 哪些内容可能复用？
- 有哪些事实风险或待验证点？
- 它可能关联到哪些主题？

这一层不追求输出完整观点，只负责把原文读懂并压缩。

所有正式知识文档只要被实际创建或修改，都必须在 frontmatter 中记录更新时间：

```yaml
updated_at: "YYYY-MM-DD"
```

这条规则适用于 10 来源精炼、20 主题页、30 可复用资产和 40 输出。修改正文、关系链接、标签、状态、证据来源或其他 frontmatter 字段，都必须同步更新 `updated_at`。批量脚本如果实际改写文件，也必须更新该字段。只读审查不更新；追加型运行日志继续使用事件 `timestamp`。

### 20-topic-pages

放跨来源综合后的主题页。

主题页不是文章，也不是资料堆积。它应该围绕一个明确问题，综合多个来源形成阶段性判断。

一个合格主题页至少要回答：

- 这个主题页讨论什么问题？
- 当前来源支持了哪些判断？
- 哪些地方仍然不确定？
- 可以沉淀哪些可复用资产？
- 可以支持哪些输出？
- 与哪些其他主题有关？

主题页是知识库的中枢层。没有主题页，知识库容易变成来源摘要仓库；主题页过多或过碎，又会变成新的垃圾站。

### 30-reusable-assets

放可以跨场景复用的知识资产。

典型类型包括：

- 方法论：一套可重复执行的方法
- 案例：可被引用和类比的具体案例
- 金句表达：可复用的表达、判断、定义
- 框架图谱：结构、分类、流程、模型
- 清单模板：可直接用于执行或检查的列表

注意：不是所有主题都应该生成方法论。资产必须有明确复用价值，不能为了填满文件夹而生产。

### 40-outputs

放面向真实使用场景的输出。

典型类型包括：

- 费曼解释：把复杂问题讲给非专业读者听
- 文章草稿：可继续编辑发布的内容
- 方案素材：可用于咨询、汇报、产品设计、业务方案
- 决策备忘：辅助做选择和判断
- 复盘记录：对一次行动或项目进行结构化总结

40 层内容默认应该具备可读性和可迁移性。除非明确标注为个人案例，否则不要把某个用户的私有目录、批次编号、本机路径写成方法论主体。

文章草稿分为三个成熟度：`article_seed`、`article_draft`、`publishable_draft`。`article_seed` 只是选题和结构素材；`article_draft` 是内部可读的完整草稿；`publishable_draft` 需要标题候选、发布编辑卡片（文章体裁、选题切口、目标读者、核心论断、关键证据/素材）、按体裁选择的正文结构、强开头、具体场景、反例或张力、可复用金句、行动性结尾和发布前事实核查清单。升级到发布级草稿时，应按 `references/publishable-article-workflow.md` 执行。

## 这个系统如何判断“什么时候可以输出”

系统不鼓励“读一篇就产出一堆内容”。默认使用晋升机制，但不同产物使用不同门槛：

1. 来源数量足够：主题页、方法论、框架、方案、文章通常至少 3 个相关来源；案例和金句表达可以来自 1 个强来源
2. 问题清晰：能被表达成一个具体问题
3. 可复用：存在方法、案例、表达、框架或清单价值
4. 有输出场景：可以支持文章、方案、解释、决策或项目
5. 风险可控：事实风险已标注，必要时进入核查队列

评分越高，越适合从 10 层晋升到 20、30、40。

如果只满足部分条件，应先保留为主题候选，而不是强行生成主题页、资产或输出。

系统现在区分两条晋升通道：

- 重资产通道：主题页、方法论、框架图谱、方案素材、文章草稿、决策备忘。要求更强证据，通常需要 3 个以上来源。
- 轻资产通道：案例、反例、金句表达、定义、区分、警示、隐喻。可以从 1 个强来源生成，但必须标注来源、使用场景和事实边界。
- 导航通道：MOC/索引页强调路由和可追溯，不按主题页的 3 来源综合门槛处理。

每轮晋升后还要检查产物组合是否失衡。如果案例长期为 0、金句表达过少、MOC 和主题页长期不增长，或候选长期停留在 `unclassified`，需要先做候选拆分和缺口修正，再继续生成重资产。

## 适合谁

适合：

- 长期阅读电子书、公众号、文章、报告的人
- 希望把阅读转化为文章、课程、咨询、研究、产品判断的人
- 希望在一台电脑上运行多个独立研究员，分别研究不同主题或项目的人
- 使用 Obsidian 或本地 Markdown 文件管理知识的人
- 不满足于“收藏”和“摘要”，希望建立可复用知识系统的人

不适合：

- 只想快速总结一篇文章的人
- 不愿意定期做主题整理和输出评审的人
- 期待完全自动生成可靠结论、无需人工判断的人
- 把知识库当成原文备份仓库的人

## 安装方式

完整安装说明见 [INSTALL.zh-CN.md](INSTALL.zh-CN.md)。

### 运行要求

最低要求：

- Python 3.10 或更高版本
- Ruby 2.7 或更高版本，仅在使用公众号库管理脚本时需要
- 一个可读写的本地知识库目录

可选依赖：

- `pypdf`、`PyPDF2` 或 `pdfplumber`：用于文本型 PDF 提取
- OCR 工具：用于扫描版 PDF 或图片型材料，本包不内置 OCR

Markdown、TXT、HTML、DOCX、EPUB 的基础提取主要依赖 Python 标准库。

### 安装到 Codex

把整个技能目录安装到 Codex 的 skills 目录下：

```bash
~/.codex/skills/knowledge-base-manager
```

安装后，确认至少包含：

```text
knowledge-base-manager/
├── SKILL.md
├── README.md
├── INSTALL.zh-CN.md
├── LICENSE
├── CHANGELOG.md
├── SECURITY.md
├── references/
├── scripts/
├── tests/
└── examples/
```

在 Codex 中使用时，可以直接说：

```text
使用 knowledge-base-manager 初始化我的知识库
```

或者：

```text
使用 knowledge-base-manager 处理这批未读文章
```

### 跨平台使用

其他 Agent 平台不一定识别 Codex 的 `SKILL.md` 格式。此时可以把本包作为“指令 + 脚本工具包”使用：

1. 将整个目录复制到目标平台可访问的位置。
2. 把 `README.md` 作为用户说明。
3. 把 `SKILL.md` 作为 Agent 系统提示或工具说明的主入口。
4. 按需把 `references/` 中的文件作为可检索知识或长期上下文。
5. 暴露 `scripts/` 中的命令给 Agent 执行。

最低可用能力不依赖 Codex：只要能运行本地 Python 脚本，就可以初始化、审计、维护索引、做晋升评审和质量检查。

### 脚本模式

即使没有 Agent 平台，也可以直接运行部分确定性命令。

检查包是否满足发布要求：

```bash
python3 scripts/kb_manager.py package-lint --strict
```

初始化知识库配置：

```bash
python3 scripts/kb_manager.py init \
  --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json \
  --ai-knowledge-base /absolute/path/to/AI-Knowledge-Base \
  --ebooks /absolute/path/to/Sources/Ebooks \
  --articles /absolute/path/to/Sources/Articles \
  --public-accounts /absolute/path/to/Sources/Public-Accounts \
  --apply
```

验证知识库配置：

```bash
python3 scripts/kb_manager.py validate-config --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json
python3 scripts/kb_manager.py doctor --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json
```

## 第一次使用

如果你已经有自己的资料目录，需要告诉 Codex 三类路径：

1. 原始资料在哪里  
   例如：电子书目录、公众号文章目录、网页剪藏目录

2. AI 知识库输出到哪里  
   例如：你的 Obsidian vault 或某个 Markdown 知识库目录

3. 你希望如何映射五层目录  
   例如：系统、来源精炼、主题页、可复用资产、输出

如果你没有现成目录，可以让系统从零创建一个默认结构。

如果你要创建多个研究员，需要额外说明：

1. 研究员名称和研究范围
   例如：AI 知识管理研究员、餐饮行业研究员、产品经理研究员、课程学习研究员

2. 该研究员的独立输入和输出目录
   每个研究员应有自己的原文库、AI 知识库和 `00-system/active` 运行状态。

3. 是否允许共享方法
   默认只共享方法、rubric、模板和闭环经验，不共享未经显式导入的领域结论。

## 常见使用方式

### 初始化知识库

```text
使用 knowledge-base-manager 从零初始化一个知识库
```

系统会创建基础目录、配置文件和系统索引。

### 初始化一个研究员

```text
使用 knowledge-base-manager 初始化一个研究员，研究主题是 AI 知识管理
```

系统会为该研究员创建或映射独立的来源库、AI 知识库、系统状态和质量门禁。多个研究员可以共用同一套技能包，但不能共用同一套 `processed-index.jsonl`、`active-run-state.json`、验证结果或输出目录，除非这是一个明确设计过的共享研究项目。

### 处理未读资料

```text
处理 20 篇未读公众号文章
```

系统会读取未处理来源，生成来源精炼，并更新索引。

重复识别优先使用解析后的来源路径，并以内容哈希作为跨路径迁移的兜底证据。旧索引缺少输出路径时，只有在对应的正式精炼文件已经存在时才会自动修复；中断在精炼阶段的任务也可由正式文件和索引恢复为已提交。系统不会仅凭标题把两份资料合并。

### 做晋升评审

```text
根据已经处理的来源，评审哪些主题可以晋升
```

系统会生成或更新主题聚类、晋升评审、资产与输出候选。

### 生成一个完整闭环

```text
选择一个主题，生成主题页、可复用资产和一个输出
```

系统会优先使用已有来源精炼和主题页，而不是重新从原文开始。

### 检查知识库健康度

```text
审计这个知识库的 20、30、40 是否健康
```

系统会检查关系、双链、主题过载、资产失衡、输出质量、事实核查状态、生命周期状态和定期健康度。知识晋升不是单向过程；已经晋升的主题页、资产和输出也可能因为证据不足、结构失败、过时、重复、低复用或被新知识替代而进入 `needs_revision`、`needs_evidence`、`parked`、`superseded`、`deprecated` 或 `archived`。

## 和普通总结工具的区别

普通总结工具通常只回答：

> 这篇文章讲了什么？

这个系统还会继续追问：

- 这篇内容应该进入哪个主题？
- 它支持了什么判断？
- 它能不能变成方法、案例、表达或框架？
- 它能不能支撑一篇文章、一个方案或一次解释？
- 它有哪些事实风险？
- 它和已有知识有什么关系？

因此，它更像一个知识生产系统，而不是一个摘要工具。

在多研究员定位下，它进一步像一个“研究员操作系统”：不同研究员各自积累领域知识，方法层持续共享和进化，避免所有主题混在一个知识库里互相污染。

## 和 Karpathy 风格 LLM Wiki 的区别

Karpathy 风格 LLM Wiki 更强调把信息整理成面向 LLM 使用的 Wiki，让模型可以读取、检索和组合。

`knowledge-base-manager` 更强调人的研究和输出流程：

- 从来源精炼开始，而不是直接堆 Wiki 页面
- 强制区分来源、主题、资产、输出
- 引入晋升评审，避免内容无限膨胀
- 引入质量门，检查可迁移性、事实风险和输出可用性
- 兼容 Obsidian 的标签、双链和 MOC

简单说：

- LLM Wiki 更偏“让模型能读”
- 本系统更偏“让人能判断、复用和输出”

两者可以结合：LLM Wiki 可作为检索和上下文层，本系统可作为知识生产和质量控制层。

## 和费曼方法如何兼容

费曼方法适合放在 40-outputs 里，作为一种输出形式。

但不建议一开始就对所有来源做费曼解释。更合理的流程是：

1. 先做来源精炼
2. 多个来源聚合成主题页
3. 判断这个主题是否适合解释给非专业读者
4. 再生成费曼解释

这样费曼解释不是“单篇文章的浅层转述”，而是基于多个来源和主题判断后的清晰表达。

## Obsidian 使用建议

如果知识库放在 Obsidian 中，建议：

- 每个文件保留少量稳定标签
- 使用双链连接真正相关的主题、资产和输出
- 不要把每个名词都做成标签
- 使用 MOC 管理主题入口
- 定期检查空双链和断链

系统提供 `obsidian_linker.py` 用于维护 frontmatter、标签、双链和 MOC。

## 质量边界

这个系统可以帮助阅读、压缩、结构化、综合和输出，但它不等于事实核查系统。

涉及以下内容时，需要额外验证：

- 公司、人物、市场、政策、法律、医学、金融等高风险事实
- 最新数据、最新事件、最新产品信息
- 作者在原文中的判断性结论
- 可能被正式发布、汇报或用于决策的内容

系统会标注 `fact_check_required`，但是否完成事实核查，需要看验证记录。

## 当前成熟度

这个项目当前是 `v0.7.7`，可以作为 Beta 版使用：

- 支持初始化和目录映射
- 支持来源处理和索引
- 支持主题晋升评审
- 支持资产和输出候选
- 支持 Obsidian 关系维护
- 支持质量门、事实核查队列和输出评审
- 支持新用户端到端测试

但它还不是完全成熟的产品级系统：

- 语义聚类仍然需要更多真实样本验证
- 高风险事实核查仍需要人工或外部来源介入
- 输出质量评审需要持续积累标准
- 不同用户的目录习惯需要更多 profile 示例
- Codex 之外的平台目前主要通过脚本模式或指令包适配，不保证所有平台开箱即用

## 发布与维护

本项目使用语义版本号。当前公开版本为 `v0.7.7`。审计与事务流水线共享来源—精炼对账器，可恢复日期改名、来源目录迁移、Unicode 标点变化和失效输出路径；只有唯一匹配才自动认领，临时文件和歧义匹配继续保留为待处理。下一批迁移输出质量和编辑成熟度治理。

发布到 GitHub 前至少运行：

```bash
python3 scripts/kb_manager.py package-lint --strict
python3 scripts/architecture_check.py --strict
python3 tests/e2e_new_user.py
python3 tests/test_kb_manager.py
python3 tests/test_pipeline.py
python3 tests/test_architecture.py
python3 tests/run_all.py
```

架构治理采用棘轮策略：`architecture-contract.json` 记录当前复杂度上限、目标规模、旧 CLI 契约和允许依赖。当前上限只用于禁止系统继续恶化；每完成一次模块抽离，都必须下调相应上限，直到 `kb_manager.py`、`kb_pipeline.py` 和 `SKILL.md` 收敛到目标规模。

第一批模块化内核已经抽离到 `kbm/domain` 和 `kbm/platform`。旧知识库不需要立即修改配置，会被兼容识别为一个隐式研究员；新初始化可以使用 `--researcher-id`、`--researcher-name` 和 `--research-domain` 写入明确身份。每个研究员的系统文件和设备本地运行目录按身份隔离。

发布包必须包含：

- `LICENSE`
- `CHANGELOG.md`
- `SECURITY.md`
- `INSTALL.zh-CN.md`
- `README.md`
- `SKILL.md`
- `references/`
- `scripts/`
- `tests/`
- `examples/`

## README 维护规则

README 是中文用户理解和安装本系统的入口文档，必须随技能一起更新。本说明覆盖当前技能的定位、目录模型、使用流程、质量边界、跨平台使用方式和发布检查要求。

当以下内容发生变化时，必须同步检查并更新 README：

- 系统定位或适用边界变化
- 默认目录模型或配置方式变化
- 新增、删除或改名核心命令
- 来源处理、晋升评审、资产生成、输出生成流程变化
- 质量门、事实核查、输出评审规则变化
- 安装方式、初始化方式、新用户流程变化
- 示例 profile 或可迁移设计边界变化
- 跨平台适配方式变化
- 版本、许可证、安全边界或发布流程变化
- 原文库配置、`source_libraries` 字段或原文追溯规则变化

发布或分发前必须运行：

```bash
python3 scripts/kb_manager.py package-lint --strict
```

如果 README 缺失关键中文说明，或 README 早于技能核心文件，检查会失败。此时不能把技能视为可分发版本，必须先更新 README。

## 给新用户的建议

第一次使用时，不要一次性处理几百篇文章。

建议从一个小闭环开始：

1. 选择 5 到 10 篇有价值的来源
2. 生成来源精炼
3. 做一次主题晋升评审
4. 只选择一个主题生成主题页
5. 只生成一个可复用资产和一个输出
6. 用质量门检查结果
7. 再决定是否扩大批量

这个系统的价值不在于快速制造文件，而在于让知识可以持续进入判断、复用和产出。
