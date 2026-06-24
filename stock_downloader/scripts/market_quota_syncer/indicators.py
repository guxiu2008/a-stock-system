#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情同步工具 - 技术指标计算模块
"""

import pandas as pd
import numpy as np


class MarketTechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: list[int] = None) -> pd.DataFrame:
        """计算均线"""
        if periods is None:
            periods = [5, 10, 20, 30, 60, 120]
        
        result = pd.DataFrame()
        result['ts_code'] = df['ts_code']
        result['trade_date'] = df['trade_date']
        
        for period in periods:
            result[f'ma{period}'] = df['close'].rolling(window=period).mean()
        
        return result
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """计算MACD"""
        result = pd.DataFrame()
        result['ts_code'] = df['ts_code']
        result['trade_date'] = df['trade_date']
        
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        result['macd'] = macd_line
        result['macd_signal'] = signal_line
        result['macd_hist'] = histogram
        
        return result
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """计算KDJ"""
        result = pd.DataFrame()
        result['ts_code'] = df['ts_code']
        result['trade_date'] = df['trade_date']
        
        low_list = df['low'].rolling(window=n, min_periods=1).min()
        high_list = df['high'].rolling(window=n, min_periods=1).max()
        
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        rsv = rsv.fillna(50)
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        result['kdj_k'] = k
        result['kdj_d'] = d
        result['kdj_j'] = j
        
        return result
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, periods: list[int] = None) -> pd.DataFrame:
        """计算RSI"""
        if periods is None:
            periods = [6, 12, 24]
        
        result = pd.DataFrame()
        result['ts_code'] = df['ts_code']
        result['trade_date'] = df['trade_date']
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        for period in periods:
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            # 处理除零情况：当avg_loss为0时，RSI设为100
            rs = avg_gain / avg_loss.where(avg_loss != 0, np.nan)
            rsi = np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))
            result[f'rsi{period}'] = rsi
        
        return result
    
    @staticmethod
    def calculate_boll(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """计算布林带"""
        result = pd.DataFrame()
        result['ts_code'] = df['ts_code']
        result['trade_date'] = df['trade_date']
        
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        result['boll_upper'] = sma + (std_dev * std)
        result['boll_mid'] = sma
        result['boll_lower'] = sma - (std_dev * std)
        
        return result
    
    @classmethod
    def calculate_all(cls, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        if df.empty:
            return pd.DataFrame()
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        ma_df = cls.calculate_ma(df)
        macd_df = cls.calculate_macd(df)
        kdj_df = cls.calculate_kdj(df)
        rsi_df = cls.calculate_rsi(df)
        boll_df = cls.calculate_boll(df)
        
        result = ma_df.copy()
        result = result.merge(macd_df, on=['ts_code', 'trade_date'], how='left')
        result = result.merge(kdj_df, on=['ts_code', 'trade_date'], how='left')
        result = result.merge(rsi_df, on=['ts_code', 'trade_date'], how='left')
        result = result.merge(boll_df, on=['ts_code', 'trade_date'], how='left')
        
        return result