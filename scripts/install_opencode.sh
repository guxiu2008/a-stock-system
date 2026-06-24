#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
SKILLS_DIR="$OPENCODE_CONFIG_DIR/skills"
AGENTS_DIR="$OPENCODE_CONFIG_DIR/agents/stock-team"
ENV_FILE="${OPENCODE_ENV_FILE:-$HOME/.opencode/.env}"
PROJECT_ENV="$ROOT_DIR/.env"

PYTHON_BIN_DEFAULT="${PYTHON_BIN:-/workspace/stock_downloader/venv/bin/python}"
STOCK_DB_DEFAULT="${STOCK_DB_PATH:-/workspace/stock_downloader/stock_data.db}"
ARCHIVE_DIR_DEFAULT="${A_STOCK_ARCHIVE_DIR:-$ROOT_DIR/skills/a-stock-advisor/archive}"

mkdir -p "$SKILLS_DIR" "$AGENTS_DIR" "$(dirname "$ENV_FILE")" "$ARCHIVE_DIR_DEFAULT"

ln -sfn "$ROOT_DIR/skills/a-stock-advisor" "$SKILLS_DIR/a-stock-advisor"
ln -sfn "$ROOT_DIR/skills/tavily-search" "$SKILLS_DIR/tavily-search"
ln -sfn "$ROOT_DIR/skills/macro-policy-scraper" "$SKILLS_DIR/macro-policy-scraper"

for agent in "$ROOT_DIR"/agents/stock-team/*.md; do
  ln -sfn "$agent" "$AGENTS_DIR/$(basename "$agent")"
done

if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

add_env() {
  local key="$1"
  local value="$2"
  if ! grep -q "^${key}=" "$ENV_FILE"; then
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

if [ -f "$PROJECT_ENV" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    add_env "$key" "$value"
  done < "$PROJECT_ENV"
else
  add_env "STOCK_DB_PATH" "$STOCK_DB_DEFAULT"
  add_env "PYTHON_BIN" "$PYTHON_BIN_DEFAULT"
  add_env "TAVILY_SEARCH_SCRIPT" "$ROOT_DIR/skills/tavily-search/scripts/tavily_search.py"
  add_env "A_STOCK_NEWS_CACHE" "/tmp/a_stock_news_cache.json"
  add_env "A_STOCK_ARCHIVE_DIR" "$ARCHIVE_DIR_DEFAULT"
  if ! grep -q '^TAVILY_API_KEY=' "$ENV_FILE"; then
    printf 'TAVILY_API_KEY=\n' >> "$ENV_FILE"
  fi
fi

chmod +x "$ROOT_DIR/skills/tavily-search/scripts/tavily_search.py"
chmod +x "$ROOT_DIR/skills/a-stock-advisor/scripts/daily_pick.py"
chmod +x "$ROOT_DIR/skills/a-stock-advisor/scripts/evaluate_stock.py"

cat <<EOF
================================================================================
                     A 股选股系统 - 安装完成
================================================================================

项目根目录: $ROOT_DIR

已安装 opencode 资产:
  ✅ $SKILLS_DIR/a-stock-advisor -> $ROOT_DIR/skills/a-stock-advisor
  ✅ $SKILLS_DIR/tavily-search -> $ROOT_DIR/skills/tavily-search
  ✅ $SKILLS_DIR/macro-policy-scraper -> $ROOT_DIR/skills/macro-policy-scraper
  ✅ $AGENTS_DIR/*.md -> $ROOT_DIR/agents/stock-team/*.md

存档目录（分月存放）:
  📁 $ARCHIVE_DIR_DEFAULT

环境配置文件:
  📄 $ENV_FILE

接下来:
  1. 编辑 $ENV_FILE，填写 TAVILY_API_KEY（如需联网新闻验证）
  2. 重启 opencode 使 skill/agent 生效
  3. 在 opencode 中直接说"今天帮我选股"即可使用

GitHub 维护提示:
  - 所有配置和脚本都在 $ROOT_DIR 下
  - 根目录 .env.example 是配置模板，可复制为 .env 自定义
  - scripts/install_opencode.sh 一键安装到任何机器
  - archive/ 目录已在 .gitignore 中，不会提交报告文件

================================================================================
EOF
