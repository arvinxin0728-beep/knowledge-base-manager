# 安装与验证

本文说明如何把 `knowledge-base-manager` 安装到不同使用环境中。

## 运行要求

最低要求：

- Python 3.10 或更高版本
- Ruby 2.7 或更高版本，仅在使用公众号库管理脚本时需要
- 一个可读写的本地知识库目录

可选依赖：

- `pypdf`、`PyPDF2` 或 `pdfplumber`：用于文本型 PDF 提取
- OCR 工具：用于扫描版 PDF 或图片型材料，本包不内置 OCR

Markdown、TXT、HTML、DOCX、EPUB 的基础提取主要依赖 Python 标准库。

## 安装到 Codex

把整个目录放到：

```bash
~/.codex/skills/knowledge-base-manager
```

目录至少应包含：

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

在 Codex 中可以直接说：

```text
使用 knowledge-base-manager 初始化我的知识库
```

## 安装到其他 Agent 平台

其他 Agent 平台不一定识别 Codex 的 `SKILL.md` 格式。此时把本包作为“指令 + 脚本工具包”使用：

1. 将整个目录复制到目标平台可访问的位置。
2. 把 `README.md` 作为用户说明。
3. 把 `SKILL.md` 作为 Agent 系统提示或工具说明的主入口。
4. 按需把 `references/` 中的文件作为可检索知识或长期上下文。
5. 暴露 `scripts/` 中的命令给 Agent 执行。

最低可用能力不依赖 Codex：只要能运行本地 Python 脚本，就可以初始化、审计、维护索引、做晋升评审和质量检查。

## 脚本模式

即使没有 Agent 平台，也可以直接运行部分确定性命令。

查看包是否满足发布要求：

```bash
python3 scripts/kb_manager.py package-lint --strict
```

初始化一个知识库配置：

```bash
python3 scripts/kb_manager.py init \
  --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json \
  --ai-knowledge-base /absolute/path/to/AI-Knowledge-Base \
  --ebooks /absolute/path/to/Sources/Ebooks \
  --articles /absolute/path/to/Sources/Articles \
  --public-accounts /absolute/path/to/Sources/Public-Accounts \
  --apply
```

这里的 `--ebooks`、`--articles`、`--public-accounts` 是原文库路径；`--ai-knowledge-base` 是处理后知识库路径。原文库和 AI 知识库可以相邻，也可以放在完全不同的位置，但不要把原文直接存进 `10-source-refinements`。

验证配置：

```bash
python3 scripts/kb_manager.py validate-config --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json
python3 scripts/kb_manager.py doctor --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json
```

运行质量门：

```bash
python3 scripts/kb_manager.py quality-gate \
  --config /absolute/path/to/AI-Knowledge-Base/00-system/kb-config.json \
  --strict
```

## 发布前验证

发布到 GitHub 前至少运行：

```bash
python3 scripts/kb_manager.py package-lint --strict
python3 scripts/architecture_check.py --strict
python3 tests/run_all.py
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```

还必须确认四研究员合成验收通过、工作区干净、发布包不含个人路径、MCP 配置、凭证、节点 ID 或企业知识。全部通过后，才可以视为满足 `v0.8.0` Beta 发布门槛。

## 注意事项

- 不要把个人路径、私有目录结构、未脱敏材料放进通用 profile。
- `examples/profiles/8xx/` 只是一个示例 profile，不是默认推荐结构。
- 对外发布的输出内容需要额外事实核查。
- 本系统不会自动替你判断版权许可，用户需要确保自己有权处理相关材料。
