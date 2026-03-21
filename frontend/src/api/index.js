import request from './request.js'

// 获取信号列表
export const getSignals = (type) => {
  return request.get('/api/signals', { params: { signal_type: type } })
}

// 获取持仓
export const getPortfolio = () => {
  return request.get('/api/portfolio')
}

// 获取资产走势
export const getAssetsChart = (days = 90) => {
  return request.get('/api/assets/chart', { params: { days } })
}

// 获取任务日志
export const getTaskLogs = (limit = 20) => {
  return request.get('/api/task-logs', { params: { limit } })
}

// 创建交易记录
export const createTrade = (data) => {
  return request.post('/api/trades', data)
}

// 忽略信号
export const ignoreSignal = (id, notes = '') => {
  return request.post(`/api/signals/${id}/ignore`, { notes })
}

// 手动触发数据同步
export const runDailySync = () => {
  return request.post('/api/run-daily-sync')
}

// 获取股票详情
export const getStockDetail = (code) => {
  return request.get(`/api/stock/${code}/detail`)
}
