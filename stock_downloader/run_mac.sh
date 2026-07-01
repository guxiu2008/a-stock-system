#!/bash/sh

./venv_mac/bin/python ./scripts/asset_registry/cli.py --update-all --db ./stock_data.db

./venv_mac/bin/python ./scripts/market_quota_syncer/cli.py --sync-all --db ./stock_data.db

./venv_mac/bin/python ./scripts/money_flow_analyst/cli.py --update-all --db ./stock_data.db

./venv_mac/bin/python ./scripts/dividend_yield_tracker/cli.py --sync-history --db ./stock_data.db

./venv_mac/bin/python ./scripts/fundamental_master/cli.py --update --db ./stock_data.db

./venv_mac/bin/python ./scripts/macro_policy_scrapper/cli.py --update-all --db ./stock_data.db
