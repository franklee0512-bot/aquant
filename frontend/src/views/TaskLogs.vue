<template>
  <div class="logs-page">
    <div class="page-header">
      <h2>任务日志</h2>
      <p class="subtitle">数据同步任务执行记录</p>
    </div>

    <div class="logs-list">
      <div
        v-for="log in logs"
        :key="log.id"
        :class="['log-card', log.status]"
      >
        <div class="log-header">
          <div class="log-title">
            <el-icon :size="18" :class="log.status">
              <SuccessFilled v-if="log.status === 'success'" />
              <WarningFilled v-else-if="log.status === 'warning'" />
              <CircleCloseFilled v-else-if="log.status === 'failed'" />
              <Loading v-else />
            </el-icon>
            <span class="task-name">{{ log.task_name }}</span>
          </div>
          <span class="log-time">{{ formatDateTime(log.created_at) }}</span>
        </div>

        <div class="log-body">
          <p class="log-message">{{ log.message }}</p>
        </div>

        <div class="log-footer">
          <span :class="['status-badge', log.status]">
            {{ getStatusText(log.status) }}
          </span>
        </div>
      </div>

      <div v-if="logs.length === 0" class="empty">
        <el-icon :size="48" color="#5a6a8a"><List /></el-icon>
        <p>暂无任务日志</p>
      </div>
    </div>

    <div class="refresh-hint">
      <el-icon><Refresh /></el-icon>
      <span>自动刷新已开启</span>
    </div>
  </div>
</template>

<script>
export default { name: 'TaskLogList' }
</script>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTaskLogs } from '../api/index.js'
import { formatDateTime } from '../utils/index.js'

const logs = ref([])
let refreshTimer = null

const getStatusText = (status) => {
  const map = {
    'success': '成功',
    'warning': '警告',
    'failed': '失败',
    'running': '运行中'
  }
  return map[status] || status
}

const fetchLogs = async () => {
  try {
    const res = await getTaskLogs(20)
    logs.value = res || []
  } catch (e) {
    ElMessage.error('获取日志失败')
  }
}

onMounted(() => {
  fetchLogs()
  // 每10秒刷新一次
  refreshTimer = setInterval(fetchLogs, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.logs-page { color: #e0e6ed; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; font-weight: 600; margin-bottom: 6px; }
.subtitle { color: #8fa4c0; font-size: 14px; }

.logs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s;
  border-left: 4px solid transparent;
}

.log-card.success {
  border-left-color: #67c23a;
  background: rgba(103, 194, 58, 0.05);
}

.log-card.warning {
  border-left-color: #e6a23c;
  background: rgba(230, 162, 60, 0.05);
}

.log-card.failed {
  border-left-color: #f56c6c;
  background: rgba(245, 108, 108, 0.05);
}

.log-card.running {
  border-left-color: #409eff;
  background: rgba(64, 158, 255, 0.05);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-title .el-icon.success { color: #67c23a; }
.log-title .el-icon.warning { color: #e6a23c; }
.log-title .el-icon.failed { color: #f56c6c; }
.log-title .el-icon.running { color: #409eff; animation: spin 1s linear infinite; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.task-name {
  font-size: 15px;
  font-weight: 500;
}

.log-time {
  color: #8fa4c0;
  font-size: 13px;
}

.log-body {
  margin-bottom: 12px;
}

.log-message {
  color: #b0c0d0;
  font-size: 14px;
  line-height: 1.6;
}

.log-footer {
  display: flex;
  justify-content: flex-end;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.success {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
}

.status-badge.warning {
  background: rgba(230, 162, 60, 0.15);
  color: #e6a23c;
}

.status-badge.failed {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.status-badge.running {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #5a6a8a;
}

.empty p {
  margin-top: 16px;
  font-size: 14px;
}

.refresh-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
  padding: 12px;
  color: #5a6a8a;
  font-size: 13px;
}

.refresh-hint .el-icon {
  animation: spin 2s linear infinite;
}
</style>
