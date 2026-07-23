# Architecture（架构手册）
> 面向产出的研究型知识管理系统 — 业务架构与系统架构

---

## 一、业务架构

### 核心模型：五层知识管线

原文库（Source Libraries: ebooks, public accounts, articles） → 10-来源精炼（逐篇精炼笔记, Gate-10 quality gate） → 20-主题页（语义聚类, 推广评分 5 维度） → 30-可复用资产（Methods, Cases, Expressions, Frameworks） → 40-输出（费曼解释, 文章草稿, 方案材料, 决策备忘录）

**价值流：** 原始材料（大量、混乱、未结构化） → 阅读 + 精炼 → 单篇理解（结构化笔记，事实标记） → 聚类 + 推广评分 → 主题判断（综合多源，有明确问题） → 资产提取 → 可复用构件（方法、案例、表达、框架） → 组装 → 对外产出（面向读者的知识产品）

### 用户工作流

1. 新增来源到原文库（电子书 / 公众号 / 文章 / 网页）
2. 运行管线：`pipeline.py discover → extract → claim → submit → commit`
3. Gate-10 检查精炼质量（结构完整性、内容 integrity、批次重复率）
4. `manager.py promote` 做主题聚类与 5 维度评分
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
