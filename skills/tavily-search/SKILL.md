---
name: tavily-search
description: 通过 Tavily API 进行网页搜索，返回搜索结果和摘要。当用户要求搜索网页/查找来源/找链接且 web_search 不可用时使用。
---

# Tavily Search

使用 Tavily API 进行网页搜索。

## 环境要求

需要设置 Tavily API Key：
- 环境变量: `TAVILY_API_KEY`
- 或配置文件: `~/.opencode/.env` 添加 `TAVILY_API_KEY=...`

脚本路径可通过 `TAVILY_SEARCH_SCRIPT` 环境变量覆盖，默认为本仓库内的 `skills/tavily-search/scripts/tavily_search.py`。

## 使用方法

### 搜索命令

```bash
TS="${TAVILY_SEARCH_SCRIPT:-skills/tavily-search/scripts/tavily_search.py}"

# 默认 JSON 格式
${PYTHON_BIN:-python3} $TS --query "..." --max-results 5

# 包含简短答案
${PYTHON_BIN:-python3} $TS --query "..." --max-results 5 --include-answer

# Markdown 格式输出
${PYTHON_BIN:-python3} $TS --query "..." --max-results 5 --format md

# Brave 风格输出
${PYTHON_BIN:-python3} $TS --query "..." --max-results 5 --format brave
```

## 输出格式

### raw (默认)
```json
{
  "query": "...",
  "results": [{"title": "...", "url": "...", "content": "..."}]
}
```

### brave
```json
{
  "query": "...",
  "results": [{"title": "...", "url": "...", "snippet": "..."}]
}
```

### md
Markdown 格式列表，包含标题、链接和摘要

## 注意事项

- 默认 `max-results` 保持较小（3-5），减少 token 消耗
- 优先返回 URL 和摘要，仅在需要时获取完整页面