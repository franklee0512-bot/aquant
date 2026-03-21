<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h2>持仓管理</h2>
      <p class="subtitle">实时监控持仓盈亏</p>
    </div>

    <!-- 汇总卡片 -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="card-title">总资产</div>
        <div class="card-value">{{ formatMoney(summary.total_value) }}</div>
        <div class="card-change" :class="{ positive: summary.total_pnl >= 0, negative: summary.total_pnl < 0 }">
          {{ formatPercent(summary.total_pnl / (summary.total_value - summary.total_pnl) * 100) }}
        </div>
      </div>
      <div class="summary-card">
        <div class="card-title">长线市值</div>
        <div class="card-value">{{ formatMoney(summary.long_total) }}</div>
        <div class="card-change" :class="{ positive: summary.long_pnl >= 0, negative: summary.long_pnl < 0 }">
          {{ formatMoney(summary.long_pnl) }}
        </div>
      </div>
      <div class="summary-card">
        <div class="card-title">短线市值</div>
        <div class="card-value">{{ formatMoney(summary.short_total) }}</div>
        <div class="card-change" :class="{ positive: summary.short_pnl >= 0, negative: summary.short_pnl < 0 }">
          {{ formatMoney(summary.short_pnl) }}
        </div>
      </div>
    </div>

    <!-- 持仓列表 -->
    <div class="positions-section">
      <div class="section-tabs">
        <div :class="['section-tab', { active: activeTab === 'long' }]" @click="activeTab = 'long'">
          <el-icon><TrendCharts /></el-icon>
          <span>长线池</span>
          <span v-if="longPositions.length" class="badge blue">{{ longPositions.length }}</span>
        </div>
        <div :class="['section-tab', { active: activeTab === 'short' }]" @click="activeTab = 'short'">
          <el-icon><Lightning /></el-icon>
          <span>短线池</span>
          <span v-if="shortPositions.length" class="badge orange">{{ shortPositions.length }}</span>
        </div>
      </div>

      <div class="positions-list">
        <div v-for="pos in currentPositions" :key="pos.code" class="position-card">
          <div class="position-header">
            <div class="stock-info">
              <span class="stock-name">{{ pos.name || pos.code }}</span>
              <span class="stock-code">{{ pos.code }}</span>
            </div>
            <div class="pnl-badge" :class="{ profit: pos.floating_pnl >= 0, loss: pos.floating_pnl < 0 }">
              {{ formatPercent(pos.floating_pnl_pct) }}
            </div>
          </div>

          <div class="position-body">
            <div class="info-grid">
              <div class="info-item">
                <span class="label">持仓成本</span>
                <span class="value">{{ formatMoney(pos.avg_cost) }}</span>
              </div>
              <div class="info-item">
                <span class="label">当前价</span>
                <span class="value">{{ formatMoney(pos.current_price) }}</span>
              </div>
              <div class="info-item">
                <span class="label">持仓数量</span>
                <span class="value">{{ pos.total_shares }}</span>
              </div>
              <div class="info-item">
                <span class="label">市值</span>
                <span class="value">{{ formatMoney(pos.market_value) }}</span>
              </div>
            </div>

            <div class="pnl-row">
              <span class="label">浮动盈亏</span>
              <span class="value" :class="{ profit: pos.floating_pnl >= 0, loss: pos.floating_pnl < 0 }">
                {{ formatMoney(pos.floating_pnl) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="currentPositions.length === 0" class="empty">
          <el-icon :size="48" color="#5a6a8a"><Wallet /></el-icon>
          <p>暂无{{ activeTab === 'long' ? '长线' : '短线' }}持仓</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: 'PortfolioPage' }
</script>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPortfolio } from '../api/index.js'
import { formatMoney, formatPercent } from '../utils/index.js'

const activeTab = ref('long')
const portfolio = ref({
  long_positions: [],
  short_positions: [],
  summary: {
    long_total: 0,
    long_pnl: 0,
    short_total: 0,
    short_pnl: 0,
    total_value: 0,
    total_pnl: 0
  }
})

const longPositions = computed(() => portfolio.value.long_positions || [])
const shortPositions = computed(() => portfolio.value.short_positions || [])
const summary = computed(() => portfolio.value.summary || {})

const currentPositions = computed(() => {
  const list = activeTab.value === 'long' ? longPositions.value : shortPositions.value
  return list.sort((a, b) => (b.floating_pnl_pct || 0) - (a.floating_pnl_pct || 0))
})

const fetchPortfolio = async () => {
  try {
    const res = await getPortfolio()
    if (res) {
      portfolio.value = res
    }
  } catch (e) {
    ElMessage.error('获取持仓失败')
  }
}

onMounted(() => {
  fetchPortfolio()
  // 每30秒刷新一次
  setInterval(fetchPortfolio, 30000)
})
</script>

<style scoped>
.portfolio-page { color: #e0e6ed; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; font-weight: 600; margin-bottom: 6px; }
.subtitle { color: #8fa4c0; font-size: 14px; }

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.summary-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.card-title {
  color: #8fa4c0;
  font-size: 13px;
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  color: #e0e6ed;
  margin-bottom: 6px;
}

.card-change {
  font-size: 14px;
  font-weight: 500;
}

.card-change.positive { color: #f56c6c; }
.card-change.negative { color: #67c23a; }

.positions-section {
  background: rgba(255,255,255,0.02);
  border-radius: 16px;
  padding: 16px;
}

.section-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.section-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.section-tab:hover {
  background: rgba(64, 158, 255, 0.1);
}

.section-tab.active {
  background: rgba(64, 158, 255, 0.2);
  border-color: rgba(64, 158, 255, 0.4);
  color: #409eff;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 4px;
}

.badge.blue {
  background: #409eff;
  color: white;
}

.badge.orange {
  background: #e6a23c;
  color: white;
}

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.position-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s;
}

.position-card:hover {
  border-color: rgba(64, 158, 255, 0.3);
}

.position-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-name {
  font-size: 17px;
  font-weight: 600;
}

.stock-code {
  color: #8fa4c0;
  font-size: 13px;
  background: rgba(255,255,255,0.06);
  padding: 4px 10px;
  border-radius: 4px;
}

.pnl-badge {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  background: rgba(255,255,255,0.08);
}

.pnl-badge.profit {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.pnl-badge.loss {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.info-item {
  text-align: center;
}

.info-item .label {
  display: block;
  color: #8fa4c0;
  font-size: 12px;
  margin-bottom: 4px;
}

.info-item .value {
  font-size: 14px;
  font-weight: 500;
  color: #e0e6ed;
}

.pnl-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
}

.pnl-row .label {
  color: #8fa4c0;
  font-size: 13px;
}

.pnl-row .value {
  font-size: 16px;
  font-weight: 600;
}

.pnl-row .value.profit { color: #f56c6c; }
.pnl-row .value.loss { color: #67c23a; }

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #5a6a8a;
}

.empty p {
  margin-top: 16px;
  font-size: 14px;
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .section-tabs {
    flex-direction: column;
  }

  .section-tab {
    justify-content: center;
  }
}
</style>
