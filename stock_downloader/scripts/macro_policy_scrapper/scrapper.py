#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取工具 - 主类
"""

import datetime
from typing import Optional, List, Dict, Any
from collections import Counter

import pandas as pd

from .database import MacroPolicyScrapperDatabase as MacroPolicyDB
from .fetcher import DataFetcher


class MacroPolicyScrapper:
    """宏观政策抓取主类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化宏观政策抓取器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db = MacroPolicyDB(db_path)
        self.fetcher = None
    
    def _ensure_fetcher(self):
        """确保数据获取器已初始化"""
        if self.fetcher is None:
            self.fetcher = DataFetcher()
    
    def _filter_existing_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤掉已存在的记录
        
        Args:
            df: 待保存的DataFrame
        
        Returns:
            过滤后的DataFrame
        """
        if df.empty:
            return df
        
        new_records = []
        for _, row in df.iterrows():
            if not self.db.narrative_exists(
                row['event_date'],
                row['source'],
                row['title']
            ):
                new_records.append(row)
        
        return pd.DataFrame(new_records)
    
    def update_news(self, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None,
                   limit: int = 100,
                   force_update: bool = False) -> int:
        """
        更新新闻快讯
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 返回数量限制
            force_update: 是否强制更新（不检查是否已存在）
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        if not start_date:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
        
        df = self.fetcher.fetch_news(start_date, end_date, limit)
        if df.empty:
            self.db.log_update('news', 'Tushare新闻', 0, 'success', '无新数据')
            return 0
        
        # 过滤已存在的记录
        if not force_update:
            df = self._filter_existing_records(df)
        
        if df.empty:
            self.db.log_update('news', 'Tushare新闻', 0, 'success', '无新数据')
            print("新闻数据已是最新，无需更新")
            return 0
        
        # 逐条保存，避免内存占用过大
        count = 0
        for i in range(len(df)):
            row_df = df.iloc[i:i+1]
            saved = self.db.save_macro_narratives(row_df)
            count += saved
        
        self.db.log_update('news', 'Tushare新闻', count, 'success')
        print(f"新闻快讯更新完成，共 {count} 条记录")
        return count
    
    def update_eco_cal(self, start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      force_update: bool = False) -> int:
        """
        更新经济日历
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force_update: 是否强制更新
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        if not start_date:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y%m%d')
        
        df = self.fetcher.fetch_eco_cal(start_date, end_date)
        if df.empty:
            self.db.log_update('eco_cal', 'Tushare经济日历', 0, 'success', '无新数据')
            return 0
        
        if not force_update:
            df = self._filter_existing_records(df)
        
        if df.empty:
            self.db.log_update('eco_cal', 'Tushare经济日历', 0, 'success', '无新数据')
            print("经济日历数据已是最新，无需更新")
            return 0
        
        count = 0
        for i in range(len(df)):
            row_df = df.iloc[i:i+1]
            saved = self.db.save_macro_narratives(row_df)
            count += saved
        
        self.db.log_update('eco_cal', 'Tushare经济日历', count, 'success')
        print(f"经济日历更新完成，共 {count} 条记录")
        return count
    
    def update_all(self, start_date: Optional[str] = None,
                  end_date: Optional[str] = None,
                  force_update: bool = False):
        """更新所有数据"""
        print("=" * 60)
        print("开始更新宏观政策数据")
        print("=" * 60)
        
        total_count = 0
        
        try:
            count = self.update_news(start_date, end_date, force_update=force_update)
            total_count += count
        except Exception as e:
            print(f"更新新闻快讯失败: {e}")
            self.db.log_update('news', 'Tushare新闻', 0, 'failed', str(e))
        
        try:
            count = self.update_eco_cal(start_date, end_date, force_update=force_update)
            total_count += count
        except Exception as e:
            print(f"更新经济日历失败: {e}")
            self.db.log_update('eco_cal', 'Tushare经济日历', 0, 'failed', str(e))
        
        print("=" * 60)
        print(f"宏观政策数据更新完成，共 {total_count} 条新记录")
        print("=" * 60)
    
    # ==================== Agent 专属接口 ====================
    
    def get_current_policy_focus(self, days: int = 30, top_n: int = 5) -> Dict[str, Any]:
        """
        获取当前政策聚焦点
        
        Args:
            days: 统计天数
            top_n: 返回前N个
        
        Returns:
            包含政策聚焦信息的字典
        """
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y%m%d')
        
        df = self.db.get_narratives_by_date_range(start_date, end_date, min_importance=3)
        
        if df.empty:
            return {
                'message': '无相关政策数据',
                'focus_sectors': [],
                'period': f'过去{days}天'
            }
        
        # 统计行业关键词
        all_sectors = []
        for sectors in df['sectors'].dropna():
            if isinstance(sectors, list):
                all_sectors.extend(sectors)
            elif isinstance(sectors, str):
                all_sectors.append(sectors)
        
        sector_counts = Counter(all_sectors)
        top_sectors = sector_counts.most_common(top_n)
        
        # 统计关键词
        all_keywords = []
        for keywords in df['keywords'].dropna():
            if isinstance(keywords, list):
                all_keywords.extend(keywords)
            elif isinstance(keywords, str):
                all_keywords.append(keywords)
        
        keyword_counts = Counter(all_keywords)
        top_keywords = keyword_counts.most_common(top_n * 2)
        
        focus_list = [f"{i+1}. {sector}" for i, (sector, count) in enumerate(top_sectors)]
        
        return {
            'message': f"当前政策聚焦：{'，'.join(focus_list)}",
            'focus_sectors': top_sectors,
            'top_keywords': top_keywords,
            'total_records': len(df),
            'period': f'过去{days}天'
        }
    
    def check_event_impact(self, sector: str, days: int = 30) -> Dict[str, Any]:
        """
        检查特定行业的事件影响
        
        Args:
            sector: 行业名称
            days: 检查天数
        
        Returns:
            包含事件影响信息的字典
        """
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y%m%d')
        
        df = self.db.get_narratives_by_date_range(start_date, end_date)
        
        if df.empty:
            return {
                'sector': sector,
                'has_impact': False,
                'message': f'近期无关于"{sector}"的政策事件',
                'events': []
            }
        
        # 筛选相关事件
        related_events = []
        for _, row in df.iterrows():
            sectors = row.get('sectors', [])
            keywords = row.get('keywords', [])
            
            sector_list = sectors if isinstance(sectors, list) else []
            keyword_list = keywords if isinstance(keywords, list) else []
            
            if sector in sector_list or sector in keyword_list:
                related_events.append({
                    'date': row['event_date'],
                    'source': row['source'],
                    'title': row['title'],
                    'importance': row.get('importance', 3),
                    'sentiment': row.get('sentiment'),
                    'summary': row.get('summary')
                })
        
        if not related_events:
            return {
                'sector': sector,
                'has_impact': False,
                'message': f'近期无关于"{sector}"的政策事件',
                'events': []
            }
        
        # 统计情感
        sentiments = [e['sentiment'] for e in related_events if e['sentiment']]
        sentiment_counts = Counter(sentiments)
        
        # 重要事件筛选
        important_events = [e for e in related_events if e['importance'] >= 4]
        
        return {
            'sector': sector,
            'has_impact': True,
            'message': f'近期有{len(related_events)}条关于"{sector}"的政策事件，其中重要事件{len(important_events)}条',
            'total_events': len(related_events),
            'important_events': len(important_events),
            'sentiment_distribution': dict(sentiment_counts),
            'events': related_events[:10]  # 返回最近10条
        }
    
    def is_macro_safe_period(self, days: int = 14) -> Dict[str, Any]:
        """
        判断当前是否为宏观安全期
        
        Args:
            days: 检查天数
        
        Returns:
            包含安全期判断信息的字典
        """
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y%m%d')
        
        df = self.db.get_narratives_by_date_range(start_date, end_date)
        
        if df.empty:
            return {
                'is_safe': True,
                'message': '近期无政策事件，默认判定为安全期',
                'risk_signals': [],
                'support_signals': []
            }
        
        risk_keywords = ['严打', '整顿', '监管', '风险', '加息', '收紧', '限制', '禁止']
        support_keywords = ['支持', '鼓励', '扶持', '降准', '降息', '优惠', '补贴']
        
        risk_events = []
        support_events = []
        
        for _, row in df.iterrows():
            title = row['title']
            summary = row.get('summary', '')
            text = title + ' ' + (summary or '')
            sentiment = row.get('sentiment')
            importance = row.get('importance', 3)
            
            # 风险信号 - 修复逻辑：先检查sentiment，再检查关键词（不使用else）
            is_risk = False
            if (sentiment == '严打' or sentiment == '规范') and importance >= 3:
                risk_events.append({
                    'date': row['event_date'],
                    'title': title,
                    'importance': importance
                })
                is_risk = True
            
            if not is_risk and importance >= 3:
                for kw in risk_keywords:
                    if kw in text:
                        risk_events.append({
                            'date': row['event_date'],
                            'title': title,
                            'importance': importance
                        })
                        break
            
            # 支持信号 - 同样修复逻辑
            is_support = False
            if sentiment == '支持' and importance >= 3:
                support_events.append({
                    'date': row['event_date'],
                    'title': title,
                    'importance': importance
                })
                is_support = True
            
            if not is_support and importance >= 3:
                for kw in support_keywords:
                    if kw in text:
                        support_events.append({
                            'date': row['event_date'],
                            'title': title,
                            'importance': importance
                        })
                        break
        
        risk_count = len(risk_events)
        support_count = len(support_events)
        
        is_safe = risk_count == 0
        
        if is_safe:
            if support_count > 0:
                message = f'当前为宏观安全期，无风险信号，有{support_count}条支持信号'
            else:
                message = '当前为宏观安全期，无明显风险或支持信号'
        else:
            message = f'当前存在{risk_count}条风险信号，需谨慎'
        
        return {
            'is_safe': is_safe,
            'message': message,
            'risk_count': risk_count,
            'support_count': support_count,
            'risk_signals': risk_events[:5],
            'support_signals': support_events[:5]
        }
    
    # ==================== 查询代理方法 ====================
    
    def get_narratives_by_date_range(self, start_date: str, end_date: str,
                                     source: Optional[str] = None,
                                     min_importance: Optional[int] = None) -> pd.DataFrame:
        return self.db.get_narratives_by_date_range(start_date, end_date, source, min_importance)
    
    def get_narratives_by_keyword(self, keyword: str, limit: int = 100) -> pd.DataFrame:
        return self.db.get_narratives_by_keyword(keyword, limit)
    
    def get_last_update_time(self, data_type: str, source: Optional[str] = None) -> Optional[str]:
        return self.db.get_last_update_time(data_type, source)