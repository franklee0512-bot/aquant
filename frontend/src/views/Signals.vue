<template>
  <div class="signals-page">
    <div class="page-header">
      <h2>今日信号</h2>
      <p class="subtitle">{{ pendingCount }} 个待处理信号</p>
    </div>

    <div class="sub-tabs">
      <div :class="['sub-tab', { active: activeTab === 'long' }]" @click="activeTab = 'long'">
        <el-icon><TrendCharts /></el-icon>
        <span>长线</span>
        <span v-if="longSignals.length" class="badge">{{ longSignals.length }}</span>
      </div>
      <div :class="['sub-tab', { active: activeTab === 'short' }]" @click="activeTab = 'short'">
        <el-icon><Lightning /></el-icon>
        <span>短线</span>
        <span v-if="shortSignals.length" class="badge">{{ shortSignals.length }}</span>
      </div>
    </div>

    <div class="signals-list">
      <div v-for="signal in filteredSignals" :key="signal.id" :class="['signal-card', { urgent: isUrgent(signal) }]">
        <div class="signal-header">
          <div class="stock-info">
            <span class="stock-name">{{ signal.name || signal.code }}</span>
            <span class="stock-code">{{ signal.code }}</span>
          </div>
          <div class="action-badge" :style="{ background: getActionColor(signal.action) }">{{ signal.action }}</div>
        </div>

        <div class="signal-body">
          <div class="info-row"><span class="label">建议金额:</span><span class="value amount">{{ formatMoney(signal.position_amount) }}</span></div>
          <div class="info-row"><span class="label">触发逻辑:</span><span class="value logic">{{ signal.trigger_logic || '-' }}</span></div>
          <div class="info-row"><span class="label">有效期:</span><span class="value countdown" :class="{ expired: isExpired(signal) }">{{ getCountdown(signal.expires_at) }}</span></div>
        </div>

        <div class="signal-actions">
          <button class="btn-execute" @click="showExecuteDialog(signal)">确认执行</button>
          <button class="btn-ignore" @click="handleIgnore(signal)">忽略</button>
        </div>
      </div>

      <div v-if="filteredSignals.length === 0" class="empty">
        <el-icon :size="48" color="#5a6a8a"><Bell /></el-icon>
        <p>暂无{{ activeTab === 'long' ? '长线' : '短线' }}信号</p>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="录入成交" width="90%" style="max-width: 400px">
      <div class="execute-form" v-if="currentSignal">
        <div class="form-row"><span class="form-label">股票:</span><span class="form-value">{{ currentSignal.name }} ({{ currentSignal.code }})</span></div>
        <div class="form-row"><span class="form-label">操作:</span><span class="form-value" :style="{ color: getActionColor(currentSignal.action) }">{{ currentSignal.action }}</span></div>
        <div class="form-item"><label>成交价格</label><el-input-number v-model="executeForm.price" :precision="2" :min="0.01" style="width: 100%" /></div>
        <div class="form-item"><label>成交数量</label><el-input-number v-model="executeForm.shares" :min="100" :step="100" style="width: 100%" /></div>
        <div class="form-item"><label>手续费</label><el-input-number v-model="executeForm.commission" :precision="2" :min="0" style="width: 100%" /></div>
        <div class="form-item"><label>交易日期</label><el-date-picker v-model="executeForm.date" type="date" style="width: 100%" value-format="YYYY-MM-DD" /></div>
        <div class="form-item"><label>备注</label><el-input v-model="executeForm.notes" type="textarea" :rows="2" /></div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleExecute" :loading="submitting">确认</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'SignalList' }
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSignals, createTrade, ignoreSignal } from '../api/index.js'
import { formatMoney, getCountdown, getActionColor, formatDate } from '../utils/index.js'
import dayjs from 'dayjs'

const activeTab = ref('long')
const signals = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentSignal = ref(null)
const submitting = ref(false)
const executeForm = ref({ price: 0, shares: 100, commission: 0, date: formatDate(new Date()), notes: '' })

const longSignals = computed(() => signals.value.filter(s => s.signal_type === '长线'))
const shortSignals = computed(() => signals.value.filter(s => s.signal_type === '短线'))
const filteredSignals = computed(() => {
  const list = activeTab.value === 'long' ? longSignals.value : shortSignals.value
  return list.filter(s => s.status === 'pending' && !isExpired(s))
})
const pendingCount = computed(() => signals.value.filter(s => s.status === 'pending' && !isExpired(s)).length)

const isExpired = (signal) => { if (!signal.expires_at) return false; return dayjs(signal.expires_at).isBefore(dayjs()) }
const isUrgent = (signal) => { if (!signal.expires_at) return false; const hours = dayjs(signal.expires_at).diff(dayjs(), 'hour'); return hours <= 12 && hours > 0 }

const fetchSignals = async () => {
  loading.value = true
  try { const res = await getSignals(); signals.value = res || [] }
  catch (e) { ElMessage.error('获取信号失败') }
  finally { loading.value = false }
}

const showExecuteDialog = (signal) => {
  currentSignal.value = signal
  executeForm.value = { price: 0, shares: 100, commission: 0, date: formatDate(new Date()), notes: '' }
  dialogVisible.value = true
}

const handleExecute = async () => {
  if (!executeForm.value.price || executeForm.value.price <= 0) { ElMessage.warning('请输入成交价格'); return }
  submitting.value = true
  try {
    await createTrade({ signal_id: currentSignal.value.id, code: currentSignal.value.code, name: currentSignal.value.name, action: currentSignal.value.action, trade_type: currentSignal.value.signal_type, actual_price: executeForm.value.price, shares: executeForm.value.shares, commission: executeForm.value.commission, trade_date: executeForm.value.date, notes: executeForm.value.notes })
    ElMessage.success('交易录入成功'); dialogVisible.value = false; fetchSignals()
  } catch (e) { ElMessage.error('录入失败: ' + e.message) }
  finally { submitting.value = false }
}

const handleIgnore = async (signal) => {
  try { await ElMessageBox.confirm('确定忽略此信号?', '提示', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    await ignoreSignal(signal.id, '用户手动忽略'); ElMessage.success('已忽略'); fetchSignals()
    // eslint-disable-next-line no-empty
  } catch (e) {}
}

onMounted(fetchSignals)
</script>

<style scoped>
.signals-page { color: #e0e6ed; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; font-weight: 600; margin-bottom: 6px; }
.subtitle { color: #8fa4c0; font-size: 14px; }
.sub-tabs { display: flex; gap: 12px; margin-bottom: 20px; }
.sub-tab { display: flex; align-items: center; gap: 8px; padding: 12px 24px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; cursor: pointer; transition: all 0.3s; font-size: 15px; }
.sub-tab:hover { background: rgba(64, 158, 255, 0.1); }
.sub-tab.active { background: rgba(64, 158, 255, 0.15); border-color: rgba(64, 158, 255, 0.4); color: #409eff; }
.badge { background: #f56c6c; color: white; font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-left: 4px; }
.signals-list { display: flex; flex-direction: column; gap: 12px; }
.signal-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; transition: all 0.3s; }
.signal-card.urgent { border-color: #e6a23c; background: rgba(230, 162, 60, 0.08); }
.signal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.stock-info { display: flex; align-items: center; gap: 10px; }
.stock-name { font-size: 17px; font-weight: 600; }
.stock-code { color: #8fa4c0; font-size: 13px; background: rgba(255,255,255,0.06); padding: 4px 10px; border-radius: 4px; }
.action-badge { padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; }
.signal-body { margin-bottom: 16px; }
.info-row { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.info-row:last-child { border-bottom: none; }
.label { color: #8fa4c0; font-size: 13px; width: 70px; flex-shrink: 0; }
.value { flex: 1; font-size: 14px; }
.value.amount { color: #67c23a; font-weight: 600; }
.value.logic { color: #e0e6ed; line-height: 1.5; }
.value.countdown { color: #409eff; }
.value.countdown.expired { color: #909399; }
.signal-actions { display: flex; gap: 10px; }
.btn-execute, .btn-ignore { flex: 1; padding: 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
.btn-execute { background: linear-gradient(135deg, #409eff, #3a8ee6); color: white; }
.btn-execute:hover { background: linear-gradient(135deg, #66b1ff, #5a9eee); }
.btn-ignore { background: rgba(255,255,255,0.06); color: #8fa4c0; border: 1px solid rgba(255,255,255,0.1); }
.btn-ignore:hover { background: rgba(255,255,255,0.1); }
.empty { text-align: center; padding: 60px 20px; color: #5a6a8a; }
.empty p { margin-top: 16px; font-size: 14px; }
.execute-form { color: #e0e6ed; }
.form-row { display: flex; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
.form-label { color: #8fa4c0; width: 70px; }
.form-value { font-weight: 500; }
.form-item { margin-top: 16px; }
.form-item label { display: block; color: #8fa4c0; font-size: 13px; margin-bottom: 8px; }
:deep(.el-dialog) { background: #1a2a4a; border: 1px solid rgba(255,255,255,0.1); }
:deep(.el-dialog__title) { color: #e0e6ed; }
:deep(.el-input__wrapper) { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); }
:deep(.el-input__inner) { color: #e0e6ed; }
@media (max-width: 768px) {
  .signal-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .action-badge { align-self: flex-start; }
  .signal-actions { flex-direction: column; }
  .sub-tab { flex: 1; justify-content: center; padding: 10px 16px; font-size: 14px; }
}
</style>