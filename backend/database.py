"""
FastAPI后端数据库模块
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import pandas as pd

# 数据库连接配置 - 优先从环境变量读取（用于云端部署），否则使用默认值
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:fJ4LbIXtyIZkRsKZ@db.osviannkljvoblhxwsut.supabase.co:5432/postgres"
)

# 移除 SQLAlchemy 不支持的查询参数（如 pgbouncer=true）
clean_url = DATABASE_URL.split('?')[0] if '?' in DATABASE_URL else DATABASE_URL

engine = create_engine(
    clean_url,
    pool_pre_ping=True,
    connect_args={'connect_timeout': 30}
)


def query(sql: str, params: dict = None) -> pd.DataFrame:
    """查询数据返回DataFrame"""
    return pd.read_sql(text(sql), engine, params=params or {})


def query_one(sql: str, params: dict = None) -> Optional[Dict]:
    """查询单条记录"""
    df = query(sql, params)
    if len(df) > 0:
        return df.iloc[0].to_dict()
    return None


def execute(sql: str, params: dict = None) -> None:
    """执行SQL语句"""
    with engine.connect() as conn:
        conn.execute(text(sql), params or {})
        conn.commit()
