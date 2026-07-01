# AGENTS.md - A-Stock System

This is a monorepo for A-share (A股) automated stock analysis running on OpenCode.

## Architecture

Three independent layers, each with its own conventions:

| Layer | Directory | Purpose |
|---|---|---|
| Skills | `skills/` | OpenCode skills triggered by user queries |
| Sub-agents | `agents/stock-team/` | Specialized agents for deep analysis |
| Data Backend | `stock_downloader/` | SQLite data downloader system (has its own AGENTS.md) |

## Critical Commands (DO NOT GUESS)

**Python interpreter is NOT system python - always use the venv path:**

```bash
# Primary Python with all dependencies
PYTHON_BIN=/workspace/stock_downloader/venv/bin/python
```

### Install / Update Skills
```bash
./scripts/install_opencode.sh
# Then restart OpenCode
```

### Daily Stock Picking
```bash
# Default: mid-term swing + financial filter + web news verification
/workspace/stock_downloader/venv/bin/python skills/a-stock-advisor/scripts/daily_pick.py

# Fast mode: skip web news verification
/workspace/stock_downloader/venv/bin/python skills/a-stock-advisor/scripts/daily_pick.py --fast

# Short-term mode (2-4 week swing)
/workspace/stock_downloader/venv/bin/python skills/a-stock-advisor/scripts/daily_pick.py --mode short

# Archive report to disk (JSON + TXT, YYYY/MM structure)
/workspace/stock_downloader/venv/bin/python skills/a-stock-advisor/scripts/daily_pick.py --archive
```

### Single Stock Evaluation
```bash
/workspace/stock_downloader/venv/bin/python skills/a-stock-advisor/scripts/evaluate_stock.py 600519
```

### Syntax Verification
```bash
/workspace/stock_downloader/venv/bin/python -m py_compile \
  skills/a-stock-advisor/scripts/daily_pick.py \
  skills/a-stock-advisor/scripts/evaluate_stock.py \
  skills/a-stock-advisor/scripts/lib/*.py \
  skills/tavily-search/scripts/tavily_search.py
```

## Environment Variables

Two valid locations:
1. Project root `.env` (Git-tracked template at `.env.example`)
2. Global `~/.opencode/.env` (auto-populated by install script)

**Required:**
- `STOCK_DB_PATH=/workspace/stock_downloader/stock_data.db`
- `PYTHON_BIN=/workspace/stock_downloader/venv/bin/python`

**Optional but recommended:**
- `TAVILY_API_KEY=...` - Without this, news verification falls back to "no web access" mode
- `A_STOCK_ARCHIVE_DIR=...` - Where archived reports go

## Conventions

### Skill Workflow
1. Edit files in this repo: `skills/` or `agents/`
2. Run `./scripts/install_opencode.sh` - creates symlinks to OpenCode config
3. Restart OpenCode for changes to take effect

### Never Commit
- `stock_data.db` and other SQLite files - too large
- `venv/` directories
- `.env` with secrets
- `archive/` reports
- Any cache files

### Data Backend
- `stock_downloader/` is treated as a separate sub-project with its own `AGENTS.md`
- Work on data downloader modules: follow `stock_downloader/AGENTS.md`
- Database is at `/workspace/stock_downloader/stock_data.db` (not in this repo)

## Testing
- No formal test framework is configured
- Verify syntax with `py_compile` (see above)
- Run scripts with `--fast --json >/tmp/test.json` for smoke tests
- For data layer changes, see `stock_downloader/AGENTS.md`

## High-Signal Quick Reference

- **Entry point for skill**: `skills/a-stock-advisor/SKILL.md`
- **Shared Python lib**: `skills/a-stock-advisor/scripts/lib/`
- **Sub-agent defs**: `agents/stock-team/*.md`
- **Data layer docs**: `stock_downloader/AGENTS.md`
- **Install idempotent**: `install_opencode.sh` is safe to re-run
- **Tavily optional**: System degrades gracefully without an API key
