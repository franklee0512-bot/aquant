<template>
  <div class="app">
    <header class="header">
      <div class="header-content">
        <div class="logo">
          <el-icon :size="28" color="#409eff"><TrendCharts /></el-icon>
          <span class="title">Frank的A股投研助手</span>
        </div>
        <div class="sync-btn" @click="runSync" v-loading="syncing">
          <el-icon><Refresh /></el-icon>
          <span>同步数据</span>
        </div>
      </div>
    </header>

    <nav class="nav">
      <router-link
        v-for="route in navRoutes"
        :key="route.path"
        :to="route.path"
        :class="['nav-item', { active: $route.path === route.path }]"
      >
        <el-icon :size="18">
          <component :is="route.meta.icon" />
        </el-icon>
        <span>{{ route.meta.title }}</span>
      </router-link>
    </nav>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { runDailySync } from './api/index.js'
import { routes } from './router/index.js'

const $route = useRoute()
const syncing = ref(false)

const navRoutes = computed(() => routes.filter(route => route.meta))

const runSync = async () => {
  if (syncing.value) return
  syncing.value = true
  try {
    await runDailySync()
    ElMessage.success('数据同步完成')
    window.location.reload()
  } catch (e) {
    ElMessage.error('同步失败: ' + e.message)
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped>
.app {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 100%);
}

.header {
  background: rgba(10, 22, 40, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(90deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sync-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(64, 158, 255, 0.15);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
  color: #409eff;
}

.sync-btn:hover {
  background: rgba(64, 158, 255, 0.25);
  border-color: #409eff;
}

.nav {
  max-width: 1200px;
  margin: 0 auto;
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  color: #8fa4c0;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s;
  font-size: 14px;
}

.nav-item:hover {
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
}

.nav-item.active {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  padding-bottom: 40px;
}

@media (max-width: 768px) {
  .header-content {
    padding: 10px 12px;
  }

  .title {
    font-size: 16px;
  }

  .nav {
    padding: 8px 12px;
  }

  .nav-item {
    padding: 8px 14px;
    font-size: 13px;
  }

  .main {
    padding: 12px;
  }
}
</style>
