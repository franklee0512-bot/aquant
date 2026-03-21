import dayjs from 'dayjs'

// 格式化日期时间
export const formatDateTime = (date) => {
  if (!date) return '-'
  return dayjs(date).format('MM-DD HH:mm')
}

// 格式化日期
export const formatDate = (date) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD')
}

// 格式化金额
export const formatMoney = (num) => {
  if (num === null || num === undefined) return '-'
  return '¥' + Number(num).toFixed(2)
}

// 格式化百分比
export const formatPercent = (num, showSign = true) => {
  if (num === null || num === undefined) return '-'
  const val = Number(num).toFixed(2)
  return showSign && num > 0 ? '+' + val + '%' : val + '%'
}

// 计算倒计时
export const getCountdown = (expiresAt) => {
  if (!expiresAt) return '-'
  const now = dayjs()
  const exp = dayjs(expiresAt)
  const diff = exp.diff(now, 'second')

  if (diff <= 0) return '已过期'

  const hours = Math.floor(diff / 3600)
  const mins = Math.floor((diff % 3600) / 60)

  if (hours > 0) {
    return `${hours}小时${mins}分`
  }
  return `${mins}分钟`
}

// 获取信号状态颜色
export const getSignalStatusColor = (status) => {
  const colors = {
    'pending': '#e6a23c',
    'executed': '#67c23a',
    'ignored': '#909399',
    'expired': '#f56c6c'
  }
  return colors[status] || '#909399'
}

// 获取动作颜色
export const getActionColor = (action) => {
  return action === '买入' ? '#f56c6c' : '#67c23a'
}
