#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易日历表 (dim_trade_calendar)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class DimTradeCalendarTable:
    """交易日历表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dim_trade_calendar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT NOT NULL,
                    cal_date TEXT NOT NULL,
                    is_open INTEGER,
                    pretrade_date TEXT,
                    UNIQUE(exchange, cal_date)
                )
            """))
            conn.commit()
    
    def clear(self):
        """清空交易日历表"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DELETE FROM dim_trade_calendar"))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存交易日历"""
        if df.empty:
            return 0
        df.to_sql('dim_trade_calendar', self.db_conn.engine, if_exists='append', index=False)
        return len(df)
    
    def is_trading_day(self, date: str, exchange: str = 'SSE') -> bool:
        """判断是否为交易日"""
        with self.db_conn.get_connection() as conn:
            result = conn.execute(
                text("SELECT is_open FROM dim_trade_calendar WHERE exchange = :exchange AND cal_date = :date"),
                {"exchange": exchange, "date": date}
            ).fetchone()
        return result[0] == 1 if result else False