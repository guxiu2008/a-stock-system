#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库基础模块 - 提供统一的数据库连接
"""

from sqlalchemy import create_engine


class DatabaseConnection:
    """数据库连接基类"""
    
    _instances = {}
    
    def __new__(cls, db_path: str = "stock_data.db"):
        """单例模式，确保同一数据库只有一个连接"""
        if db_path not in cls._instances:
            instance = super().__new__(cls)
            instance.db_path = db_path
            instance.engine = create_engine(f"sqlite:///{db_path}")
            cls._instances[db_path] = instance
        return cls._instances[db_path]
    
    def get_connection(self):
        """获取数据库连接"""
        return self.engine.connect()