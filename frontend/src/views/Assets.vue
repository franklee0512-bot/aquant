<template>
  <div class="assets-page">
    <div class="page-header">
      <h2>资产走势</h2>
      <p class="subtitle">资产净值与沪深300对比</p>
    </div>

    <!-- 统计指标 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">总收益率</div>
        <div class="stat-value" :class="{ positive: stats.total_return >= 0, negative: stats.total_return < 0 }">
          {{ formatPercent(stats.total_return) }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">最大回撤</div>
        <div class="stat-value negative">
          {{ formatPercent(stats.max_drawdown) }}
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-container">
      <div ref="chartRef" class="chart"></div>
    </div>

    <!-- 时间范围选择 -->
    <div class="time-selector">
      <button
        v-for="range in timeRanges"
        :key="range.days"
        :class="['time-btn', { active: selectedRange === range.days }]"
        @click="changeRange(range.days)"
      >
        {{ range.label }}
      </button>
    </div>
  </div>
</template>

<script>
export default { name: 'AssetsChart' }
</script>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getAssetsChart } from '../api/index.js'
import { formatPercent } from '../utils/index.js'

const chartRef = ref(null)
let chart = null

const selectedRange = ref(90)
const stats = ref({
  total_return: 0,
  max_drawdown: 0
})

const timeRanges = [
  { label: '1月', days: 30 },
  { label: '3月', days: 90 },
  { label: '6月', days: 180 },
  { label: '1年', days: 365 }
]

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, 'dark', {
    renderer: 'canvas'
  })
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(26, 42, 74, 0.95)',
      borderColor: 'rgba(64, 158, 255, 0.3)',
      textStyle: { color: '#e0e6ed' }
    },
    legend: {
      data: ['我的资产', '沪深300'],
      textStyle: { color: '#8fa4c0' },
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [],
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#8fa4c0' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#8fa4c0' }
    },
    series: [
      {
        name: '我的资产',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 3, color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.01)' }
          ])
        },
        data: []
      },
      {
        name: '沪深300',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#909399', type: 'dashed' },
        data: []
      }
    ]
  })
}

const fetchData = async (days) => {
  try {
    const res = await getAssetsChart(days)
    if (res) {
      stats.value.total_return = res.total_return || 0
      stats.value.max_drawdown = res.max_drawdown || 0

      if (chart) {
        chart.setOption({
          xAxis: { data: res.dates || [] },
          series: [
            { data: res.my_assets || [] },
            { data: res.hs300 || [] }
          ]
        })
      }
    }
  } catch (e) {
    ElMessage.error('获取资产数据失败')
  }
}

const changeRange = (days) => {
  selectedRange.value = days
  fetchData(days)
}

const handleResize = () => {
  chart && chart.resize()
}

onMounted(() => {
  nextTick(() => {
    initChart()
    fetchData(selectedRange.value)
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart && chart.dispose()
})
</script>

<style scoped>
.assets-page { color: #e0e6ed; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; font-weight: 600; margin-bottom: 6px; }
.subtitle { color: #8fa4c0; font-size: 14px; }

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-label {
  color: #8fa4c0;
  font-size: 13px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
}

.stat-value.positive { color: #f56c6c; }
.stat-value.negative { color: #67c23a; }

.chart-container {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.chart {
  width: 100%;
  height: 400px;
}

.time-selector {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.time-btn {
  padding: 10px 24px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  color: #8fa4c0;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.time-btn:hover {
  background: rgba(64, 158, 255, 0.1);
}

.time-btn.active {
  background: rgba(64, 158, 255, 0.2);
  border-color: #409eff;
  color: #409eff;
}

@media (max-width: 768px) {
  .stats-row {
    flex-direction: column;
  }

  .chart {
    height: 300px;
  }

  .time-btn {
    padding: 8px 16px;
    font-size: 13px;
  }
}
</style>
