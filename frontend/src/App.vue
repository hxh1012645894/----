<script setup>
import { ref, watch } from 'vue'
import WorkSpace from './components/WorkSpace.vue'
import ReportCenter from './components/ReportCenter.vue'
import AdminPanel from './components/AdminPanel.vue'

// 当前标签页状态
const currentTab = ref('workspace')

// 文件预览状态（用于控制布局）
const filePreviewVisible = ref(false)

// 组件引用
const reportCenterRef = ref(null)
const adminPanelRef = ref(null)

// 切换标签页
const switchTab = (tab) => {
  currentTab.value = tab
  // 切换到报告中心时刷新列表
  if (tab === 'report_center' && reportCenterRef.value) {
    reportCenterRef.value.loadReports()
  }
  // 切换到管理后台时加载配置
  if (tab === 'admin' && adminPanelRef.value) {
    adminPanelRef.value.loadPrompts()
    adminPanelRef.value.loadDictionary()
  }
}

// 监听子组件的预览状态变化
const onPreviewStateChanged = (val) => {
  filePreviewVisible.value = val
}
</script>

<template>
  <div :class="filePreviewVisible ? 'full-screen' : ''">
    <!-- 头部标题 -->
    <h1 class="text-3xl font-bold text-center text-blue-800 mb-6">ISO 体系智能审核系统</h1>

    <!-- 标签页切换 -->
    <div class="flex justify-center space-x-4 mb-8" data-html2canvas-ignore="true">
      <button
        @click="switchTab('workspace')"
        :class="currentTab === 'workspace' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        🚀 审核工作台
      </button>
      <button
        @click="switchTab('report_center')"
        :class="currentTab === 'report_center' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        📁 报告中心
      </button>
      <button
        @click="switchTab('admin')"
        :class="currentTab === 'admin' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        ⚙️ 引擎配置中台
      </button>
    </div>

    <!-- 工作台 -->
    <WorkSpace v-if="currentTab === 'workspace'" />

    <!-- 报告中心 -->
    <ReportCenter
      v-if="currentTab === 'report_center'"
      ref="reportCenterRef"
      @previewStateChanged="onPreviewStateChanged"
    />

    <!-- 配置中台 -->
    <AdminPanel v-if="currentTab === 'admin'" ref="adminPanelRef" />
  </div>
</template>

<style scoped>
.full-screen {
  width: 50%;
  padding-right: 1.5rem;
  margin-left: 0;
  transition: all 0.5s ease;
}
</style>