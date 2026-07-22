# 8XX Profile Pattern

Use this reference when a user has, or wants, an 8XX-style numeric folder system. This file describes the pattern only. Do not store a specific user's absolute paths in the installed skill.

## 8XX Mapping Pattern

| Universal role | Typical 8XX folder |
|---|---|
| ebook source library | `800-电子书库` |
| public-account source library | `801-公众号库` |
| AI knowledge base | `888-AI知识库` |
| system | `888-AI知识库/00-系统` |
| source refinements | `888-AI知识库/10-来源精炼` |
| topic pages | `888-AI知识库/20-主题页/主题页` |
| MOC indexes | `888-AI知识库/20-主题页/MOC` |
| reusable assets | `888-AI知识库/30-可复用资产` |
| outputs | `888-AI知识库/40-输出` |

## User-Specific Configuration

A user's actual paths must live in their own `<ai_knowledge_base>/00-系统/kb-config.json`, not in this skill. For an 8XX user, the config usually maps:

```json
{
  "source_libraries": {
    "ebooks": "/absolute/path/to/800-电子书库",
    "public_accounts": "/absolute/path/to/801-公众号库/笔记同步助手/公众号原始文章"
  },
  "ai_knowledge_base": "/absolute/path/to/888-AI知识库",
  "mapping": {
    "system": "00-系统",
    "source_refinements": "10-来源精炼",
    "topic_pages": "20-主题页",
    "reusable_assets": "30-可复用资产",
    "outputs": "40-输出"
  },
  "topic_page_subdirs": {
    "pages": "主题页",
    "moc": "MOC"
  },
  "promotion_rules": {
    "cluster_rules": "00-系统/cluster-rules.json"
  },
  "integrations": {
    "obsidian": {
      "enabled": true,
      "taxonomy": "00-系统/obsidian-taxonomy.json"
    }
  }
}
```

Copy `examples/profiles/8xx/cluster-rules.json` and `examples/profiles/8xx/obsidian-taxonomy.json` into the configured system directory during 8XX initialization. Portable initialization must not install these personal starter topics automatically.

## Important Boundary

Do not write public-facing explanations as if `800/801/888` is the universal method. Explain the universal model first, then map it to the user's 8XX implementation as an example.
