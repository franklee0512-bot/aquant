# A股量化投研工具 - Frank的投研助手

## 项目简介

这是一个完整的A股个人量化投研系统，包含：
- **数据底座**：自动拉取A股数据，过滤ST股、小市值股，数据质量验证
- **双引擎选股**：长线价值投资 + 短线趋势交易
- **网页看板**：实时查看信号、持仓、资产走势

## 项目结构

```
aquant/
├── database_schema.sql      # 数据库表结构SQL
├── data_sync/               # 数据同步模块
│   ├── database.py         # 数据库连接
│   ├── data_fetcher.py     # 数据拉取（akshare）
│   ├── data_validator.py   # 数据质量验证
│   ├── stock_selector.py   # 双引擎选股逻辑
│   └── daily_sync.py       # 每日同步主脚本
├── backend/                 # FastAPI后端
│   ├── database.py         # 后端数据库模块
│   └── main.py             # FastAPI主程序
└── frontend/                # Vue3前端
    ├── package.json        # 依赖配置
    ├── vue.config.js       # Vue配置
    └── src/
        ├── main.js         # 入口文件
        ├── App.vue         # 主组件
        ├── router/         # 路由
        ├── api/            # API接口
        ├── utils/          # 工具函数
        └── views/          # 页面组件
            ├── Signals.vue      # 今日信号
            ├── Portfolio.vue    # 持仓管理
            ├── Assets.vue       # 资产走势
            └── TaskLogs.vue     # 任务日志
```

## 快速开始

### 1. 初始化数据库

1. 登录 Supabase (https://supabase.com)
2. 打开 SQL Editor
3. 执行 `database_schema.sql` 文件中的SQL语句
4. 所有表将自动创建

### 2. 安装Python依赖

```bash
pip install akshare pandas numpy psycopg2-binary sqlalchemy apscheduler fastapi uvicorn requests
```

### 3. 启动后端（FastAPI）

```bash
cd aquant/backend
python main.py
```

后端将在 `http://localhost:8000` 启动

### 4. 启动前端（Vue）

```bash
cd aquant/frontend
npm install
npm run serve
```

前端将在 `http://localhost:8080` 启动

### 5. 手机访问（同一WiFi下）

1. 确保手机和电脑连接同一WiFi
2. 查看电脑IP地址：
   - Windows: `ipconfig` 查看IPv4地址
   - Mac/Linux: `ifconfig` 或 `ip addr`
3. 手机浏览器访问：`http://<电脑IP>:8080`

例如：`http://192.168.1.100:8080`

## 功能说明

### 数据拉取（每日15:30后自动运行）

```bash
# 手动触发数据拉取测试
cd aquant/data_sync
python daily_sync.py
```

或者通过API：
```bash
curl -X POST http://localhost:8000/api/run-daily-sync
```

### 选股策略

**长线引擎**：
- 入池：连续3年ROE>15% 且 经营现金流/净利润>0.8
- 买入：PE-TTM跌入历史20%分位以下
- 卖出：PE-TTM达到历史80%分位 或 ROE跌破10%

**短线引擎**：
- 前置：上证指数须在20日均线之上
- 买入：股价突破20日均线 且 成交量>前5日均量×2
- 止损：跌破5日均线 或 亏损≥5%
- 止盈：涨幅达到10%

### 仓位规则

- 长线：单只上限2000元，最多5只
- 短线：单只上限3000元，最多3只

## API接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/signals` | GET | 获取待处理信号 |
| `/api/portfolio` | GET | 获取当前持仓 |
| `/api/assets/chart` | GET | 获取资产走势 |
| `/api/task-logs` | GET | 获取任务日志 |
| `/api/trades` | POST | 录入成交记录 |
| `/api/signals/{id}/ignore` | POST | 忽略信号 |
| `/api/run-daily-sync` | POST | 手动触发数据同步 |

## 注意事项

1. **数据库连接**：已配置Supabase连接信息，无需修改
2. **首次运行**：需要先执行SQL创建表，然后运行数据同步
3. **数据更新**：建议每天15:30收盘后运行数据同步
4. **手机访问**：确保电脑防火墙允许8080和8000端口

## 技术支持

- 前端：Vue 3 + Element Plus + ECharts
- 后端：FastAPI
- 数据源：AKShare（东方财富）
- 数据库：PostgreSQL (Supabase)

## 免责声明

本工具仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
# Railway deployment trigger
