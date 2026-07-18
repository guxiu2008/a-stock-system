#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主营业务构成表 (fact_revenue_segments)
存储分产品/分行业/分地区的收入构成数据
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class FactRevenueSegmentsTable:
    """主营业务构成表操作类"""

    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()

    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_revenue_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    bz_item TEXT NOT NULL,
                    bz_type TEXT NOT NULL,
                    bz_sales REAL,
                    bz_profit REAL,
                    bz_cost REAL,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date, bz_item)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rs_ts_code ON fact_revenue_segments(ts_code)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rs_end_date ON fact_revenue_segments(end_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_rs_ts_end ON fact_revenue_segments(ts_code, end_date)"))
            conn.commit()

    def save(self, df: pd.DataFrame) -> int:
        """保存主营业务构成数据（INSERT OR REPLACE 模式）"""
        if df.empty:
            return 0

        if 'ts_code' not in df.columns or 'end_date' not in df.columns or 'bz_item' not in df.columns:
            print("错误：数据缺少 ts_code / end_date / bz_item 列")
            return 0

        df = df.copy()
        if 'bz_type' not in df.columns:
            df['bz_type'] = 'U'
        else:
            df['bz_type'] = df['bz_type'].fillna('U')

        with self.db_conn.get_connection() as conn:
            count = 0
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO fact_revenue_segments
                    (ts_code, end_date, bz_item, bz_type, bz_sales, bz_profit, bz_cost, update_time)
                    VALUES (:ts_code, :end_date, :bz_item, :bz_type, :bz_sales, :bz_profit, :bz_cost, :update_time)
                """), {
                    "ts_code": row.get("ts_code"),
                    "end_date": row.get("end_date"),
                    "bz_item": row.get("bz_item") or "未分类",
                    "bz_type": row.get("bz_type") or "U",
                    "bz_sales": row.get("bz_sales"),
                    "bz_profit": row.get("bz_profit"),
                    "bz_cost": row.get("bz_cost"),
                    "update_time": row.get("update_time"),
                })
                count += 1
            conn.commit()
        return count

    def get(self, ts_code: str = None, end_date: str = None, bz_type: str = None) -> pd.DataFrame:
        """查询主营业务构成"""
        query = "SELECT * FROM fact_revenue_segments WHERE 1=1"
        params = {}

        if ts_code:
            query += " AND ts_code = :ts_code"
            params["ts_code"] = ts_code
        if end_date:
            query += " AND end_date = :end_date"
            params["end_date"] = end_date
        if bz_type:
            query += " AND bz_type = :bz_type"
            params["bz_type"] = bz_type

        query += " ORDER BY ts_code, end_date DESC, bz_sales DESC"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)

    def get_existing_by_period(self, period: str) -> set:
        """获取指定报告期已存在的股票代码集合"""
        with self.db_conn.get_connection() as conn:
            result = conn.execute(
                text("SELECT DISTINCT ts_code FROM fact_revenue_segments WHERE end_date = :end_date"),
                {"end_date": period}
            )
            return set(row[0] for row in result)
