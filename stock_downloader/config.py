#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 使用环境变量配置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# Tushare Token (必须通过环境变量配置)
# 请在 https://tushare.pro/ 注册并获取您的Token
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")

# 数据库配置
DATABASE_PATH = os.getenv("DATABASE_PATH", "stock_data.db")

# 默认下载市场
DEFAULT_MARKET = os.getenv("DEFAULT_MARKET", "A股")  # 可选: "A股", "H股", "美股"

# 下载配置
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.3"))  # 请求间隔(秒)，避免请求过快（Tushare免费版200次/分钟限制）
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # 最大重试次数
