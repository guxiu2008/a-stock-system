# AGENTS.md - Agentic Coding Guidelines

This document provides guidelines for agents working in this stock data downloader repository.

## Project Overview

This is a Python-based A-stock (A股) data download and analysis system. It uses SQLite for data storage and Tushare API for fetching stock data.

## Build/Test Commands

### Dependencies
```bash
pip install -r requirements.txt
```

### Running Modules
Each module can be run via its CLI:
```bash
# Asset Registry
python scripts/asset_registry/cli.py --update-all
python scripts/asset_registry/cli.py --query-stock 000001.SZ

# Market Quota Syncer
python scripts/market_quota_syncer/cli.py --update-all

# Money Flow Analyst
python scripts/money_flow_analyst/cli.py --update-all

# Dividend Yield Tracker
python scripts/dividend_yield_tracker/cli.py --update-all

# Fundamental Master
python scripts/fundamental_master/cli.py --update-all

# Macro Policy Scrapper
python scripts/macro_policy_scrapper/cli.py --update-all
```

### Testing
No formal test framework is configured. Manual testing is done via:
- Running CLI commands with `--help` to verify options
- Running example_usage.py files in each module directory

To run a single test manually:
```bash
python -c "from scripts.asset_registry.registry import AssetRegistry; r = AssetRegistry(); print(r.get_stock_info())"
```

### Virtual Environment
```bash
# Activate
source .venv/bin/activate

# Deactivate
deactivate
```

## Code Style Guidelines

### File Header
All Python files should start with:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module description
"""
```

### Imports
- Standard library imports first
- Third-party imports second
- Local imports third
- Each group separated by a blank line
- Use absolute imports when possible
- Add project root to path for local modules:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### Type Hints
Always use type hints for function parameters and return types:
```python
def fetch_stock_basic(self) -> pd.DataFrame:
    """Fetch stock basic information."""
    pass

def get_stock_info(self, ts_code: str = None, industry: str = None) -> Optional[pd.DataFrame]:
    pass
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `AssetRegistry`, `DatabaseConnection`)
- Functions/methods: `snake_case` (e.g., `update_stock_basic()`, `get_stock_info()`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `TUSHARE_TOKEN`, `DATABASE_PATH`)
- Variables: `snake_case` (e.g., `db_path`, `df_result`)

### Docstrings
Use Google-style docstrings for all public methods:
```python
def update_stock_basic(self) -> int:
    """
    Update stock basic information.
    
    Returns:
        Number of records updated.
    """
```

### Error Handling
- Use try/except blocks for API calls and database operations
- Print error messages instead of raising for non-critical failures
- Log failures but continue processing other items:
```python
try:
    df = self.fetcher.fetch_stock_basic()
except Exception as e:
    print(f"Failed to fetch stock basic: {e}")
    return pd.DataFrame()
```

### Database Operations
- Use SQLAlchemy with SQLite
- Use singleton pattern for DatabaseConnection
- Use parameterized queries to prevent SQL injection:
```python
query += " AND ts_code = :ts_code"
params["ts_code"] = ts_code
pd.read_sql(text(query), self.engine, params=params)
```

### API Calls
- Add delay between API calls (typically 1 second):
```python
time.sleep(1)
```
- Check for empty DataFrames before processing
- Log progress with print statements

### Configuration
- Use `config.py` for global settings
- Use `.env` file for secrets (never commit)
- Access via `os.getenv()` with defaults:
```python
DATABASE_PATH = os.getenv("DATABASE_PATH", "stock_data.db")
```

### Data Handling
- Use pandas DataFrames for tabular data
- Check `df.empty` before processing
- Use `pd.concat()` with `ignore_index=True` for combining DataFrames
- Use `drop_duplicates()` when merging data from multiple sources

### Logging
- Use print statements for progress and errors
- Use consistent formatting:
```python
print("=" * 60)
print("Starting asset registry update")
print("=" * 60)
```

### Class Structure
Follow this pattern:
```python
class AssetRegistry:
    """Main class description."""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """Initialize the registry."""
        self.db = AssetRegistryDB(db_path)
        self.fetcher = None
    
    def _ensure_fetcher(self):
        """Ensure fetcher is initialized (lazy loading)."""
        if self.fetcher is None:
            self.fetcher = DataFetcher()
    
    def update_stock_basic(self) -> int:
        """Public method with docstring."""
        self._ensure_fetcher()
        # implementation
```

### Module Structure
Each module should have:
- `__init__.py` - Package marker
- `cli.py` - Command-line interface
- `main.py` or `<module_name>.py` - Main class
- `database.py` - Database operations
- `fetcher.py` - API data fetching
- `README.md` - Module documentation
- `requirement.txt` - Module-specific dependencies (if any)

### Database Table Pattern
Each table should have a corresponding class in `scripts/lib/tables/`:
- `Dim*Table` - Dimension tables
- `Fact*Table` - Fact tables
- `Map*Table` - Mapping tables
- `*LogTable` - Log tables

### Path Handling
Use pathlib for file operations:
```python
from pathlib import Path
config_path = Path(__file__).parent / "config.yaml"
```

### Date Formats
- Use `YYYYMMDD` format for Tushare API dates
- Use `YYYY-MM-DD HH:MM:SS` format for timestamps in database
- Use `datetime` module for date manipulation

## Environment Variables Required

Create `.env` file:
```
TUSHARE_TOKEN=your_token_here
DATABASE_PATH=stock_data.db
REQUEST_DELAY=2
MAX_RETRIES=3
```

## Common Patterns

### Conditional Module Path Addition
When creating scripts that need to import from lib:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### Empty DataFrame Handling
```python
if df.empty:
    print("No data fetched")
    return pd.DataFrame()
```

### Single Instance Pattern
```python
class DatabaseConnection:
    _instances = {}
    
    def __new__(cls, db_path: str = "stock_data.db"):
        if db_path not in cls._instances:
            instance = super().__new__(cls)
            instance.db_path = db_path
            cls._instances[db_path] = instance
        return cls._instances[db_path]
```
