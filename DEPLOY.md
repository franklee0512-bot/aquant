# 云端部署指南

## 部署架构

```
Vercel (前端 Vue) ←→ Railway (后端 FastAPI + 定时任务) ←→ Supabase (PostgreSQL)
```

## 1. 部署后端到 Railway

### 步骤：
1. 访问 https://railway.app 注册/登录
2. 创建新项目 → 选择 "Deploy from GitHub repo"
3. 连接你的 GitHub 账号，选择本仓库
4. Railway 会自动识别 `railway.toml` 和 `Procfile`
5. 添加环境变量：
   - `DATABASE_URL` = 你的Supabase连接地址
6. 点击 Deploy，等待部署完成
7. 记下 Railway 分配的域名（如 `https://aquant-backend.up.railway.app`）

### 自动定时任务
后端已配置 APScheduler，每天15:30自动运行数据同步。

## 2. 部署前端到 Vercel

### 步骤：
1. 访问 https://vercel.com 注册/登录（可用GitHub账号）
2. 创建新项目 → 导入 GitHub 仓库
3. 配置：
   - Framework Preset: Vue.js
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. 添加环境变量：
   - `VUE_APP_API_URL` = Railway后端地址
5. 点击 Deploy

### 配置API地址
修改 `frontend/.env.production`：
```
VUE_APP_API_URL=https://你的railway域名
```

## 3. 更新CORS（后端）

部署后，修改 `backend/main.py` 中的 `origins` 列表，添加Vercel域名：

```python
origins = [
    "http://localhost:8080",
    "https://你的vercel域名.vercel.app",  # 添加这行
]
```

## 4. 验证部署

1. 访问 Railway 后端地址，应看到：`{"message": "A股量化投研API运行中"}`
2. 访问 Vercel 前端地址，应看到登录界面
3. 数据会自动每天15:30同步，也可手动触发：
   ```
   POST https://你的railway域名/api/run-daily-sync
   ```

## 费用说明

- **Railway**: 每月$5免费额度（足够个人使用）
- **Vercel**: 免费版无限带宽
- **Supabase**: 免费版500MB数据库（足够）

**完全免费！**

## 故障排查

### 后端无法连接数据库
检查 `DATABASE_URL` 环境变量是否正确设置

### 前端无法访问API
检查 `VUE_APP_API_URL` 是否正确指向Railway地址
检查后端CORS是否允许了Vercel域名

### 定时任务没运行
查看Railway日志，检查APScheduler是否正确启动
