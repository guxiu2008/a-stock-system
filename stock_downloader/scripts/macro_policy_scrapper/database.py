#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取工具 - 数据库操作
使用 scripts.lib 中的共享表结构
"""

from typing import Optional, List
import pandas as pd
from scripts.lib import (
    FactMacroNarrativesTable,
    MacroPolicyScrapperLogTable,
    MapIndustryStockTable,
    MapConceptStockTable,
)


class MacroPolicyScrapperDatabase:
    """宏观政策抓取数据库操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.fact_macro_narratives = FactMacroNarrativesTable(db_path)
        self.macro_policy_scrapper_log = MacroPolicyScrapperLogTable(db_path)
        self.map_industry_stock = MapIndustryStockTable(db_path)
        self.map_concept_stock = MapConceptStockTable(db_path)
    
    # ==================== 宏观政策叙事 ====================
    
    def save_macro_narratives(self, df: pd.DataFrame) -> int:
        """
        保存宏观政策叙事数据
        
        Args:
            df: 包含宏观政策叙事数据的DataFrame
        
        Returns:
            保存的记录数
        """
        return self.fact_macro_narratives.save(df)
    
    def narrative_exists(self, event_date: str, source: str, title: str) -> bool:
        """
        检查叙事记录是否已存在
        
        Args:
            event_date: 事件日期
            source: 来源
            title: 标题
        
        Returns:
            是否存在
        """
        return self.fact_macro_narratives.exists(event_date, source, title)
    
    def get_narratives_by_date_range(self, start_date: str, end_date: str,
                                     source: Optional[str] = None,
                                     min_importance: Optional[int] = None) -> pd.DataFrame:
        """
        获取指定日期范围内的宏观政策叙事
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            source: 来源筛选
            min_importance: 最低重要程度
        
        Returns:
            DataFrame
        """
        return self.fact_macro_narratives.get_by_date_range(
            start_date, end_date, source, min_importance
        )
    
    def get_narratives_by_keyword(self, keyword: str, limit: int = 100) -> pd.DataFrame:
        """
        根据关键词搜索叙事
        
        Args:
            keyword: 关键词
            limit: 返回数量限制
        
        Returns:
            DataFrame
        """
        return self.fact_macro_narratives.get_by_keyword(keyword, limit)
    
    def clear_macro_narratives(self):
        """清空宏观政策叙事表"""
        self.fact_macro_narratives.clear()
    
    # ==================== 行业/概念映射 ====================
    
    def get_industries(self) -> List[str]:
        """
        获取所有行业列表
        
        Returns:
            行业名称列表
        """
        df = self.map_industry_stock.get_all()
        if df.empty:
            return []
        return df['industry_name'].unique().tolist()
    
    def get_concepts(self) -> List[str]:
        """
        获取所有概念列表
        
        Returns:
            概念名称列表
        """
        df = self.map_concept_stock.get_all()
        if df.empty:
            return []
        return df['concept_name'].unique().tolist()
    
    # ==================== 日志 ====================
    
    def log_update(self, data_type: str, source: str, record_count: int, 
                  status: str, message: Optional[str] = None):
        """
        记录更新日志
        
        Args:
            data_type: 数据类型
            source: 数据来源
            record_count: 记录数
            status: 状态
            message: 附加信息
        """
        self.macro_policy_scrapper_log.log(data_type, source, record_count, status, message)
    
    def get_last_update_time(self, data_type: str, source: Optional[str] = None) -> Optional[str]:
        """
        获取指定数据类型的最后更新时间
        
        Args:
            data_type: 数据类型
            source: 数据来源（可选）
        
        Returns:
            最后更新时间
        """
        return self.macro_policy_scrapper_log.get_last_update_time(data_type, source)