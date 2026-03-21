-- A股量化投研工具数据库表结构
-- 在 Supabase SQL Editor 中执行此脚本

-- 1. 股票基本信息表
CREATE TABLE IF NOT EXISTS stock_basic (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    list_date DATE,
    market_cap FLOAT,
    debt_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 日线行情表
CREATE TABLE IF NOT EXISTS stock_daily (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open FLOAT, high FLOAT, low FLOAT, close FLOAT,
    volume FLOAT, amount FLOAT, turnover FLOAT,
    ma5 FLOAT, ma20 FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_code_date ON stock_daily(code, trade_date);

-- 3. 财务指标表
CREATE TABLE IF NOT EXISTS stock_finance (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    report_date DATE NOT NULL,
    pe_ttm FLOAT, pb FLOAT, roe FLOAT,
    net_profit FLOAT, cash_flow_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_finance_code ON stock_finance(code);

-- 4. 交易信号表
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL CHECK (action IN ('买入', '卖出')),
    signal_type TEXT NOT NULL CHECK (signal_type IN ('长线', '短线')),
    trigger_logic TEXT,
    position_amount FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'ignored', 'expired')),
    executed_at TIMESTAMP,
    executed_price FLOAT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);

-- 5. 任务日志表
CREATE TABLE IF NOT EXISTS task_log (
    id SERIAL PRIMARY KEY,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'warning', 'failed')),
    message TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 6. 交易记录表
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    code TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    actual_price FLOAT NOT NULL,
    shares INTEGER NOT NULL,
    commission FLOAT DEFAULT 0,
    total_amount FLOAT,
    trade_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 持仓表
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT,
    position_type TEXT NOT NULL,
    avg_cost FLOAT NOT NULL,
    total_shares INTEGER NOT NULL,
    current_price FLOAT,
    market_value FLOAT,
    floating_pnl FLOAT,
    floating_pnl_pct FLOAT,
    first_buy_date DATE,
    last_trade_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 资产历史表
CREATE TABLE IF NOT EXISTS asset_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_assets FLOAT,
    cash FLOAT,
    stock_value FLOAT,
    long_value FLOAT,
    short_value FLOAT,
    daily_pnl FLOAT,
    cumulative_pnl FLOAT,
    hs300_close FLOAT,
    hs300_return FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
