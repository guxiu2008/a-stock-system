#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库表模块
"""

# 维度表
from .dim_stock_info import DimStockInfoTable
from .dim_trade_calendar import DimTradeCalendarTable

# 映射表
from .map_industry_stock import MapIndustryStockTable
from .map_concept_stock import MapConceptStockTable

# 事实表
from .fact_financial_reports import FactFinancialReportsTable
from .fact_daily_quotes import FactDailyQuotesTable
from .fact_index_daily import FactIndexDailyTable
from .fact_dividend_history import FactDividendHistoryTable
from .fact_money_flow import FactMoneyFlowTable
from .fact_macro_narratives import FactMacroNarrativesTable
from .fact_revenue_segments import FactRevenueSegmentsTable

# 状态表
from .stock_sync_status import StockSyncStatusTable
from .index_sync_status import IndexSyncStatusTable

# 指标表
from .market_indicators import MarketIndicatorsTable

# 日志表
from .asset_registry_log import AssetRegistryLogTable
from .fundamental_master_log import FundamentalMasterLogTable
from .market_quota_log import MarketQuotaLogTable
from .dividend_yield_tracker_log import DividendYieldTrackerLogTable
from .money_flow_analyst_log import MoneyFlowAnalystLogTable
from .macro_policy_scrapper_log import MacroPolicyScrapperLogTable

__all__ = [
    # 维度表
    'DimStockInfoTable',
    'DimTradeCalendarTable',
    
    # 映射表
    'MapIndustryStockTable',
    'MapConceptStockTable',
    
    # 事实表
    'FactFinancialReportsTable',
    'FactDailyQuotesTable',
    'FactIndexDailyTable',
    'FactDividendHistoryTable',
    'FactMoneyFlowTable',
    'FactMacroNarrativesTable',
    'FactRevenueSegmentsTable',
    
    # 状态表
    'StockSyncStatusTable',
    'IndexSyncStatusTable',
    
    # 指标表
    'MarketIndicatorsTable',
    
    # 日志表
    'AssetRegistryLogTable',
    'FundamentalMasterLogTable',
    'MarketQuotaLogTable',
    'DividendYieldTrackerLogTable',
    'MoneyFlowAnalystLogTable',
    'MacroPolicyScrapperLogTable',
]
