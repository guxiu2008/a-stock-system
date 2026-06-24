#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策叙事表 (fact_macro_narratives)
"""

from typing import Optional, List
import datetime
import json
import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class FactMacroNarrativesTable:
    """宏观政策叙事表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_macro_narratives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_date TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    keywords TEXT,
                    summary TEXT,
                    importance INTEGER DEFAULT 3,
                    sentiment TEXT,
                    sectors TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(event_date, source, title)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """
        保存宏观政策叙事数据
        
        Args:
            df: 包含宏观政策叙事数据的DataFrame，需要包含以下列：
                event_date, source, title, keywords (可选), 
                summary (可选), importance (可选), sentiment (可选), sectors (可选)
        
        Returns:
            保存的记录数
        """
        if df.empty:
            return 0
        
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        count = 0
        with self.db_conn.get_connection() as conn:
            for _, row in df.iterrows():
                keywords_json = json.dumps(row.get('keywords', []), ensure_ascii=False) if pd.notna(row.get('keywords')) else None
                sectors_json = json.dumps(row.get('sectors', []), ensure_ascii=False) if pd.notna(row.get('sectors')) else None
                
                try:
                    conn.execute(text("""
                        INSERT OR REPLACE INTO fact_macro_narratives 
                        (event_date, source, title, keywords, summary, importance, sentiment, sectors, created_at, updated_at)
                        VALUES (:event_date, :source, :title, :keywords, :summary, :importance, :sentiment, :sectors, :created_at, :updated_at)
                    """), {
                        "event_date": str(row['event_date']),
                        "source": str(row['source']),
                        "title": str(row['title']),
                        "keywords": keywords_json,
                        "summary": str(row['summary']) if pd.notna(row.get('summary')) else None,
                        "importance": int(row.get('importance', 3)),
                        "sentiment": str(row.get('sentiment')) if pd.notna(row.get('sentiment')) else None,
                        "sectors": sectors_json,
                        "created_at": now,
                        "updated_at": now
                    })
                    count += 1
                except Exception as e:
                    print(f"保存记录失败: {e}")
                    continue
            conn.commit()
        
        return count
    
    def exists(self, event_date: str, source: str, title: str) -> bool:
        """检查记录是否已存在"""
        with self.db_conn.get_connection() as conn:
            result = conn.execute(text("""
                SELECT 1 FROM fact_macro_narratives 
                WHERE event_date = :event_date AND source = :source AND title = :title
                LIMIT 1
            """), {
                "event_date": event_date,
                "source": source,
                "title": title
            }).fetchone()
        return result is not None
    
    def get_by_date_range(self, start_date: str, end_date: str, 
                         source: Optional[str] = None,
                         min_importance: Optional[int] = None) -> pd.DataFrame:
        """
        获取指定日期范围内的宏观政策叙事
        
        Args:
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期 (YYYYMMDD 或 YYYY-MM-DD)
            source: 来源筛选
            min_importance: 最低重要程度
        
        Returns:
            DataFrame
        """
        query = """
            SELECT id, event_date, source, title, keywords, summary, importance, sentiment, sectors, created_at, updated_at
            FROM fact_macro_narratives
            WHERE event_date >= :start_date AND event_date <= :end_date
        """
        params = {"start_date": start_date, "end_date": end_date}
        
        if source:
            query += " AND source = :source"
            params["source"] = source
        
        if min_importance:
            query += " AND importance >= :min_importance"
            params["min_importance"] = min_importance
        
        query += " ORDER BY event_date DESC, importance DESC"
        
        with self.db_conn.get_connection() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        
        # 解析JSON字段
        if not df.empty:
            df['keywords'] = df['keywords'].apply(lambda x: json.loads(x) if x else [])
            df['sectors'] = df['sectors'].apply(lambda x: json.loads(x) if x else [])
        
        return df
    
    def get_by_keyword(self, keyword: str, limit: int = 100) -> pd.DataFrame:
        """
        根据关键词搜索
        
        Args:
            keyword: 关键词
            limit: 返回数量限制
        
        Returns:
            DataFrame
        """
        with self.db_conn.get_connection() as conn:
            df = pd.read_sql(text("""
                SELECT id, event_date, source, title, keywords, summary, importance, sentiment, sectors, created_at, updated_at
                FROM fact_macro_narratives
                WHERE keywords LIKE :keyword OR title LIKE :keyword OR summary LIKE :keyword
                ORDER BY event_date DESC
                LIMIT :limit
            """), conn, params={
                "keyword": f"%{keyword}%",
                "limit": limit
            })
        
        if not df.empty:
            df['keywords'] = df['keywords'].apply(lambda x: json.loads(x) if x else [])
            df['sectors'] = df['sectors'].apply(lambda x: json.loads(x) if x else [])
        
        return df
    
    def clear(self):
        """清空表"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DELETE FROM fact_macro_narratives"))
            conn.commit()