#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取工具 - 数据获取模块
"""

import datetime
import sys
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import Counter

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class DataFetcher:
    """数据获取类 - 从Tushare和其他来源获取宏观政策数据"""
    
    def __init__(self):
        """初始化数据获取器"""
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
        
        # 行业关键词映射
        self.sector_keywords = {
            '人工智能': ['人工智能', 'AI', '大模型', '深度学习', '机器学习', '算力'],
            '半导体': ['半导体', '芯片', '集成电路', 'EDA', '光刻机'],
            '新能源': ['新能源', '光伏', '风电', '储能', '锂电池', '充电桩'],
            '数字经济': ['数字经济', '数据要素', '东数西算', '大数据', '云计算'],
            '医药生物': ['医药', '生物', '疫苗', '创新药', '医疗器械', '医疗'],
            '消费': ['消费', '内需', '零售', '白酒', '食品', '旅游', '餐饮'],
            '房地产': ['房地产', '房产', '楼市', '住房'],
            '金融': ['金融', '银行', '证券', '保险', '基金', '降准', '降息'],
            '军工': ['军工', '国防', '航空', '航天', '舰船'],
            '汽车': ['汽车', '新能源汽车', '自动驾驶', '智能网联'],
            '通信': ['通信', '5G', '6G', '光模块', '算力网络'],
            '计算机': ['计算机', '软件', '信创', '操作系统', '国产替代'],
            '低空经济': ['低空经济', '无人机', 'eVTOL', '通用航空'],
            '新质生产力': ['新质生产力', '先进制造', '高端制造', '智能制造'],
        }
        
        # 情感关键词
        self.sentiment_keywords = {
            '支持': ['支持', '鼓励', '扶持', '促进', '推动', '利好', '优惠', '补贴', '减税'],
            '稳健': ['稳健', '平稳', '适度', '合理', '规范', '引导'],
            '规范': ['规范', '整治', '整顿', '监管', '合规', '风险'],
            '严打': ['严打', '打击', '查处', '禁止', '限制', '叫停', '整顿'],
        }
        
        # 噪音过滤关键词
        self.noise_keywords = [
            '涨停', '跌停', '大涨', '大跌', '机构预测', '分析师', '推荐', '买入', '卖出',
            '个股', '股票', '股价', '市值', '估值', 'PE', 'PB', 'EPS',
        ]
    
    def is_noise_news(self, title: str, content: Optional[str] = None) -> bool:
        """
        判断是否为噪音新闻
        
        Args:
            title: 新闻标题
            content: 新闻内容（可选）
        
        Returns:
            是否为噪音
        """
        text = title
        if content:
            text += ' ' + content
        
        text_lower = text.lower()
        for keyword in self.noise_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def extract_keywords(self, title: str, content: Optional[str] = None) -> List[str]:
        """
        提取关键词（简单版本，基于预设关键词库）
        
        Args:
            title: 标题
            content: 内容（可选）
        
        Returns:
            关键词列表
        """
        text = title
        if content:
            text += ' ' + content
        
        keywords = []
        for sector, sector_keywords in self.sector_keywords.items():
            for kw in sector_keywords:
                if kw in text:
                    if sector not in keywords:
                        keywords.append(sector)
                    if kw not in keywords and kw != sector:
                        keywords.append(kw)
        
        return keywords
    
    def extract_sectors(self, title: str, content: Optional[str] = None) -> List[str]:
        """
        提取相关行业/板块
        
        Args:
            title: 标题
            content: 内容（可选）
        
        Returns:
            行业列表
        """
        text = title
        if content:
            text += ' ' + content
        
        sectors = []
        for sector, sector_keywords in self.sector_keywords.items():
            for kw in sector_keywords:
                if kw in text:
                    if sector not in sectors:
                        sectors.append(sector)
                    break
        
        return sectors
    
    def analyze_sentiment(self, title: str, content: Optional[str] = None) -> str:
        """
        分析情感极性
        
        Args:
            title: 标题
            content: 内容（可选）
        
        Returns:
            情感类型: '支持', '稳健', '规范', '严打', 或 None
        """
        text = title
        if content:
            text += ' ' + content
        
        sentiment_counts = Counter()
        for sentiment, keywords in self.sentiment_keywords.items():
            for kw in keywords:
                if kw in text:
                    sentiment_counts[sentiment] += 1
        
        if sentiment_counts:
            return sentiment_counts.most_common(1)[0][0]
        return None
    
    def calculate_importance(self, title: str, content: Optional[str] = None, 
                            source: Optional[str] = None) -> int:
        """
        计算重要程度评分 (1-5)
        
        Args:
            title: 标题
            content: 内容
            source: 来源
        
        Returns:
            重要程度评分
        """
        score = 3
        
        # 来源权重
        if source:
            source_lower = source.lower()
            if '新闻联播' in source or '中央' in source or '国务院' in source:
                score += 2
            elif '发改委' in source or '央行' in source or '财政部' in source:
                score += 1
            elif '证券时报' in source or '上海证券报' in source or '中国证券报' in source:
                score += 0
        
        # 关键词权重
        text = title
        if content:
            text += ' ' + content
        
        high_importance_keywords = [
            '政治局会议', '中央经济工作会议', '全国两会', '国务院',
            '降准', '降息', '新质生产力', '重大政策', '重磅',
        ]
        for kw in high_importance_keywords:
            if kw in text:
                score += 1
        
        return min(5, max(1, score))
    
    def fetch_news(self, start_date: str, end_date: str, 
                  limit: int = 100) -> pd.DataFrame:
        """
        获取新闻快讯
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 返回数量限制
        
        Returns:
            新闻DataFrame
        """
        print(f"正在获取新闻快讯 ({start_date} ~ {end_date})...")
        time.sleep(1)
        
        try:
            df = self.pro.news(
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            if df.empty:
                print("未获取到新闻数据")
                return pd.DataFrame()
            
            # 处理数据
            results = []
            for _, row in df.iterrows():
                title = row.get('title', '')
                content = row.get('content', '')
                
                # 过滤噪音
                if self.is_noise_news(title, content):
                    continue
                
                event_date = row.get('pub_time', '').split(' ')[0].replace('-', '')
                if not event_date:
                    event_date = start_date
                
                keywords = self.extract_keywords(title, content)
                sectors = self.extract_sectors(title, content)
                sentiment = self.analyze_sentiment(title, content)
                importance = self.calculate_importance(title, content, 'Tushare新闻')
                
                results.append({
                    'event_date': event_date,
                    'source': 'Tushare新闻',
                    'title': title,
                    'keywords': keywords,
                    'summary': content[:200] if content else None,
                    'importance': importance,
                    'sentiment': sentiment,
                    'sectors': sectors,
                })
            
            result_df = pd.DataFrame(results)
            print(f"获取到 {len(result_df)} 条有效新闻（已过滤噪音）")
            return result_df
            
        except Exception as e:
            print(f"获取新闻数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_eco_cal(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取经济日历
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            经济日历DataFrame
        """
        print(f"正在获取经济日历 ({start_date} ~ {end_date})...")
        time.sleep(1)
        
        try:
            df = self.pro.eco_cal(
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                print("未获取到经济日历数据")
                return pd.DataFrame()
            
            # 处理数据
            results = []
            for _, row in df.iterrows():
                event_date = row.get('date', '').replace('-', '')
                if not event_date:
                    continue
                
                title = row.get('event', '')
                country = row.get('country', '')
                if country:
                    title = f"[{country}] {title}"
                
                keywords = ['经济数据', row.get('indicator', '')]
                keywords = [kw for kw in keywords if kw]
                
                importance_map = {'高': 5, '中': 3, '低': 1}
                importance = importance_map.get(row.get('priority', ''), 3)
                
                results.append({
                    'event_date': event_date,
                    'source': 'Tushare经济日历',
                    'title': title,
                    'keywords': keywords,
                    'summary': row.get('remark', ''),
                    'importance': importance,
                    'sentiment': None,
                    'sectors': ['宏观经济'],
                })
            
            result_df = pd.DataFrame(results)
            print(f"获取到 {len(result_df)} 条经济日历数据")
            return result_df
            
        except Exception as e:
            print(f"获取经济日历失败: {e}")
            return pd.DataFrame()
    
    def fetch_xwlb_mock(self, date: Optional[str] = None) -> pd.DataFrame:
        """
        模拟获取新闻联播数据（占位实现）
        
        Args:
            date: 日期 (YYYYMMDD)
        
        Returns:
            新闻联播DataFrame
        """
        print("新闻联播数据获取功能待实现（需要接入新闻联播API）")
        return pd.DataFrame()
    
    def fetch_meeting_mock(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        模拟获取重要会议纪要（占位实现）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            会议纪要DataFrame
        """
        print("重要会议纪要获取功能待实现（需要接入政府网站爬虫）")
        return pd.DataFrame()