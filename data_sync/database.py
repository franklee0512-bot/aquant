"""
数据库连接和基础操作模块
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import pandas as pd

# 数据库连接配置 - 优先从环境变量读取（用于云端部署）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:fJ4LbIXtyIZkRsKZ@db.osviannkljvoblhxwsut.supabase.co:5432/postgres"
)

class Database:
    def __init__(self):
        self.engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args={'connect_timeout': 30}
        )

    def execute(self, sql: str, params: dict = None) -> None:
        """执行SQL语句"""
        with self.engine.connect() as conn:
            conn.execute(text(sql), params or {})
            conn.commit()

    def query(self, sql: str, params: dict = None) -> pd.DataFrame:
        """查询数据返回DataFrame"""
        return pd.read_sql(text(sql), self.engine, params=params or {})

    def query_one(self, sql: str, params: dict = None) -> Optional[Dict]:
        """查询单条记录"""
        df = self.query(sql, params)
        if len(df) > 0:
            return df.iloc[0].to_dict()
        return None

    def insert_df(self, df: pd.DataFrame, table: str, if_exists: str = 'append') -> int:
        """插入DataFrame到数据库"""
        if df.empty:
            return 0
        df.to_sql(table, self.engine, if_exists=if_exists, index=False, method='multi')
        return len(df)

    def log_task(self, task_name: str, status: str, message: str = '', details: dict = None):
        """记录任务日志"""
        sql = """
        INSERT INTO task_log (task_name, status, message, details, created_at)
        VALUES (:task_name, :status, :message, CAST(:details AS JSONB), CURRENT_TIMESTAMP)
        """
        with self.engine.connect() as conn:
            conn.execute(text(sql), {
                'task_name': task_name,
                'status': status,
                'message': message,
                'details': json.dumps(details or {})
            })
            conn.commit()
        print(f"[{datetime.now()}] {task_name}: {status} - {message}")

# 全局数据库实例
db = Database()
