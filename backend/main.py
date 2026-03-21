"""
FastAPI后端主文件
A股量化投研工具API - 云端部署版
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
import database as db
import os
import sys

# 添加数据同步模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'data_sync'))

app = FastAPI(title="A股量化投研API", version="1.0.0")

# 配置CORS - 允许Vercel域名和本地开发
origins = [
    "http://localhost:8080",
    "https://localhost:8080",
    "http://localhost:3000",
    "https://localhost:3000",
    # Vercel部署后会自动添加实际域名
]
# 从环境变量读取额外允许的域名
additional_origins = os.getenv("ALLOWED_ORIGINS", "")
if additional_origins:
    origins.extend(additional_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议改为origins列表
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建后台调度器
scheduler = BackgroundScheduler()

def run_daily_sync_job():
    """定时任务：每日数据同步"""
    try:
        from daily_sync import run_daily_sync
        print(f"[{datetime.now()}] 开始定时数据同步...")
        run_daily_sync()
        print(f"[{datetime.now()}] 定时数据同步完成")
    except Exception as e:
        print(f"[{datetime.now()}] 定时数据同步失败: {e}")

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    # 添加定时任务：每天15:30运行
    scheduler.add_job(
        run_daily_sync_job,
        'cron',
        hour=15,
        minute=30,
        id='daily_sync',
        replace_existing=True
    )
    scheduler.start()
    print(f"[{datetime.now()}] 后端服务启动成功，定时任务已设置（每天15:30）")

@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    scheduler.shutdown()
    print(f"[{datetime.now()}] 后端服务关闭")


# ==================== Pydantic模型 ====================

class Signal(BaseModel):
    id: int
    code: str
    name: Optional[str]
    action: str
    signal_type: str
    trigger_logic: Optional[str]
    position_amount: Optional[float]
    created_at: datetime
    expires_at: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


class Position(BaseModel):
    code: str
    name: Optional[str]
    position_type: str
    avg_cost: float
    total_shares: int
    current_price: Optional[float]
    market_value: Optional[float]
    floating_pnl: Optional[float]
    floating_pnl_pct: Optional[float]
    first_buy_date: Optional[str]
    last_trade_date: Optional[str]


class TradeCreate(BaseModel):
    signal_id: Optional[int] = None
    code: str
    name: Optional[str] = None
    action: str
    trade_type: str
    actual_price: float
    shares: int
    commission: float = 0
    trade_date: Optional[str] = None
    notes: Optional[str] = None


class TaskLog(BaseModel):
    id: int
    task_name: str
    status: str
    message: Optional[str]
    created_at: datetime


class AssetData(BaseModel):
    date: str
    total_assets: Optional[float]
    cash: Optional[float]
    stock_value: Optional[float]
    daily_pnl: Optional[float]
    cumulative_pnl: Optional[float]
    hs300_close: Optional[float]
    hs300_return: Optional[float]


class IgnoreSignalRequest(BaseModel):
    notes: Optional[str] = None


# ==================== API路由 ====================

@app.get("/")
def root():
    return {"message": "A股量化投研API运行中", "version": "1.0.0"}


@app.get("/api/signals", response_model=List[Signal])
def get_signals(signal_type: Optional[str] = None):
    """
    获取待处理且未过期的信号列表
    可选参数：signal_type (长线/短线) 进行过滤
    """
    sql = """
    SELECT * FROM signals
    WHERE status = 'pending'
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    """
    params = {}

    if signal_type:
        sql += " AND signal_type = :signal_type"
        params['signal_type'] = signal_type

    sql += " ORDER BY created_at DESC"

    df = db.query(sql, params)

    # 处理NaN值
    df = df.where(pd.notnull(df), None)

    return df.to_dict('records')


@app.get("/api/portfolio")
def get_portfolio():
    """
    获取当前持仓和盈亏
    返回长线池和短线池的数据
    """
    # 获取所有持仓
    sql = """
    SELECT * FROM positions
    ORDER BY position_type, code
    """
    df = db.query(sql)

    # 处理NaN值
    df = df.where(pd.notnull(df), None)

    # 按类型分组
    long_positions = []
    short_positions = []

    if not df.empty:
        for _, row in df.iterrows():
            pos = row.to_dict()
            if pos.get('position_type') == '长线':
                long_positions.append(pos)
            else:
                short_positions.append(pos)

    # 计算汇总
    long_total = sum(p.get('market_value', 0) or 0 for p in long_positions)
    long_pnl = sum(p.get('floating_pnl', 0) or 0 for p in long_positions)

    short_total = sum(p.get('market_value', 0) or 0 for p in short_positions)
    short_pnl = sum(p.get('floating_pnl', 0) or 0 for p in short_positions)

    return {
        "long_positions": long_positions,
        "short_positions": short_positions,
        "summary": {
            "long_total": long_total,
            "long_pnl": long_pnl,
            "short_total": short_total,
            "short_pnl": short_pnl,
            "total_value": long_total + short_total,
            "total_pnl": long_pnl + short_pnl
        }
    }


@app.get("/api/assets/chart")
def get_assets_chart(days: int = 90):
    """
    获取资产走势数据
    含沪深300对比
    """
    sql = """
    SELECT date, total_assets, cash, stock_value, daily_pnl,
           cumulative_pnl, hs300_close, hs300_return
    FROM asset_history
    WHERE date >= CURRENT_DATE - INTERVAL ':days days'
    ORDER BY date ASC
    """
    df = db.query(sql, {'days': days})

    if df.empty:
        return {
            "dates": [],
            "my_assets": [],
            "hs300": [],
            "total_return": 0,
            "max_drawdown": 0
        }

    # 处理NaN值
    df = df.where(pd.notnull(df), None)

    # 计算收益率和最大回撤
    if len(df) > 0 and df['total_assets'].iloc[0]:
        start_value = df['total_assets'].iloc[0]
        end_value = df['total_assets'].iloc[-1]
        total_return = (end_value - start_value) / start_value * 100 if start_value > 0 else 0

        # 计算最大回撤
        max_value = df['total_assets'].expanding().max()
        drawdown = (df['total_assets'] - max_value) / max_value * 100
        max_drawdown = drawdown.min() if not drawdown.empty else 0
    else:
        total_return = 0
        max_drawdown = 0

    return {
        "dates": df['date'].dt.strftime('%Y-%m-%d').tolist(),
        "my_assets": df['total_assets'].tolist(),
        "hs300": df['hs300_close'].tolist(),
        "hs300_return": df['hs300_return'].tolist(),
        "total_return": round(total_return, 2),
        "max_drawdown": round(max_drawdown, 2)
    }


@app.get("/api/task-logs", response_model=List[TaskLog])
def get_task_logs(limit: int = 20):
    """
    获取最近任务日志
    """
    sql = """
    SELECT id, task_name, status, message, created_at
    FROM task_log
    ORDER BY created_at DESC
    LIMIT :limit
    """
    df = db.query(sql, {'limit': limit})
    df = df.where(pd.notnull(df), None)
    return df.to_dict('records')


@app.post("/api/trades")
def create_trade(trade: TradeCreate):
    """
    录入真实成交记录
    """
    try:
        # 计算总金额
        total_amount = trade.actual_price * trade.shares + trade.commission

        # 如果没有指定交易日期，使用今天
        trade_date = trade.trade_date or datetime.now().strftime('%Y-%m-%d')

        # 插入交易记录
        sql = """
        INSERT INTO trades
        (signal_id, code, name, action, trade_type, actual_price, shares,
         commission, total_amount, trade_date, notes, created_at)
        VALUES
        (:signal_id, :code, :name, :action, :trade_type, :actual_price, :shares,
         :commission, :total_amount, :trade_date, :notes, CURRENT_TIMESTAMP)
        RETURNING id
        """
        result = db.query(sql, {
            'signal_id': trade.signal_id,
            'code': trade.code,
            'name': trade.name or '',
            'action': trade.action,
            'trade_type': trade.trade_type,
            'actual_price': trade.actual_price,
            'shares': trade.shares,
            'commission': trade.commission,
            'total_amount': total_amount,
            'trade_date': trade_date,
            'notes': trade.notes or ''
        })

        trade_id = result.iloc[0]['id'] if not result.empty else None

        # 更新信号状态（如果有signal_id）
        if trade.signal_id:
            db.execute("""
                UPDATE signals
                SET status = 'executed',
                    executed_at = CURRENT_TIMESTAMP,
                    executed_price = :price
                WHERE id = :signal_id
            """, {'signal_id': trade.signal_id, 'price': trade.actual_price})

        # 更新持仓表
        update_position(trade.code, trade.name, trade.trade_type, trade.action,
                       trade.actual_price, trade.shares)

        return {"success": True, "trade_id": trade_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def update_position(code: str, name: str, position_type: str, action: str,
                   price: float, shares: int):
    """更新持仓"""
    # 查询现有持仓
    existing = db.query_one(
        "SELECT * FROM positions WHERE code = :code",
        {'code': code}
    )

    if action == '买入':
        if existing:
            # 更新持仓
            old_shares = existing['total_shares']
            old_cost = existing['avg_cost']
            new_shares = old_shares + shares
            new_cost = (old_cost * old_shares + price * shares) / new_shares

            db.execute("""
                UPDATE positions
                SET avg_cost = :cost,
                    total_shares = :shares,
                    last_trade_date = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE code = :code
            """, {'code': code, 'cost': new_cost, 'shares': new_shares})
        else:
            # 新建持仓
            db.execute("""
                INSERT INTO positions
                (code, name, position_type, avg_cost, total_shares,
                 first_buy_date, last_trade_date, updated_at)
                VALUES
                (:code, :name, :type, :cost, :shares,
                 CURRENT_DATE, CURRENT_DATE, CURRENT_TIMESTAMP)
            """, {
                'code': code, 'name': name or code, 'type': position_type,
                'cost': price, 'shares': shares
            })

    elif action == '卖出':
        if existing:
            old_shares = existing['total_shares']
            new_shares = old_shares - shares

            if new_shares <= 0:
                # 清仓
                db.execute("DELETE FROM positions WHERE code = :code", {'code': code})
            else:
                # 减仓（保持成本价不变）
                db.execute("""
                    UPDATE positions
                    SET total_shares = :shares,
                        last_trade_date = CURRENT_DATE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE code = :code
                """, {'code': code, 'shares': new_shares})


@app.post("/api/signals/{signal_id}/ignore")
def ignore_signal(signal_id: int, request: IgnoreSignalRequest):
    """
    忽略某条信号
    """
    try:
        db.execute("""
            UPDATE signals
            SET status = 'ignored',
                notes = :notes
            WHERE id = :signal_id
        """, {'signal_id': signal_id, 'notes': request.notes or '用户忽略'})

        return {"success": True, "message": "信号已忽略"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-daily-sync")
def run_daily_sync():
    """
    手动触发数据拉取
    """
    try:
        from daily_sync import run_daily_sync as sync
        success = sync()

        if success:
            return {"success": True, "message": "数据同步完成"}
        else:
            raise HTTPException(status_code=500, detail="数据同步失败")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{code}/detail")
def get_stock_detail(code: str):
    """
    获取股票详情
    """
    # 基本信息
    basic = db.query_one(
        "SELECT * FROM stock_basic WHERE code = :code",
        {'code': code}
    )

    # 最新日线
    daily = db.query_one("""
        SELECT * FROM stock_daily
        WHERE code = :code
        ORDER BY trade_date DESC LIMIT 1
    """, {'code': code})

    # 最新财务
    finance = db.query_one("""
        SELECT * FROM stock_finance
        WHERE code = :code
        ORDER BY report_date DESC LIMIT 1
    """, {'code': code})

    # 历史信号
    signals_df = db.query("""
        SELECT * FROM signals
        WHERE code = :code
        ORDER BY created_at DESC LIMIT 10
    """, {'code': code})

    return {
        "basic": basic,
        "daily": daily,
        "finance": finance,
        "recent_signals": signals_df.to_dict('records') if not signals_df.empty else []
    }


# 导入pandas
import pandas as pd

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
