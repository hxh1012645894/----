<script setup>
import { ref, onMounted } from 'vue'
import PlatformEntry from './components/PlatformEntry.vue'
import WorkSpace from './components/WorkSpace.vue'
import ReportCenter from './components/ReportCenter.vue'
import AuditConfig from './components/AuditConfig.vue'
import AccidentUpload from './components/AccidentUpload.vue'
import AccidentLedger from './components/AccidentLedger.vue'

// 系统选择状态
const currentSystem = ref(null)  // null | 'audit' | 'accident'

// 标签页状态
const currentTab = ref({
  audit: 'workspace',
  accident: 'upload'
})

// 文件预览状态
const filePreviewVisible = ref(false)

// 组件引用
const reportCenterRef = ref(null)
const auditConfigRef = ref(null)
const accidentUploadRef = ref(null)
const accidentLedgerRef = ref(null)

// 已加载标记
const loadedTabs = ref({
  audit: { report_center: false, config: false },
  accident: { upload: false, ledger: false }
})

// 选择系统
const selectSystem = (system) => {
  currentSystem.value = system
  localStorage.setItem('ehs_system', system)
}

// 返回平台入口
const backToPlatform = () => {
  currentSystem.value = null
  localStorage.removeItem('ehs_system')
}

// 切换标签页
const switchTab = (tab) => {
  if (currentSystem.value === 'audit') {
    currentTab.value.audit = tab
    // 懒加载
    if (tab === 'report_center' && !loadedTabs.value.audit.report_center && reportCenterRef.value) {
      reportCenterRef.value.loadReports()
      loadedTabs.value.audit.report_center = true
    }
    if (tab === 'config' && !loadedTabs.value.audit.config && auditConfigRef.value) {
      auditConfigRef.value.loadPrompts()
      auditConfigRef.value.loadDictionary()
      loadedTabs.value.audit.config = true
    }
  } else if (currentSystem.value === 'accident') {
    currentTab.value.accident = tab
    // 懒加载
    if (tab === 'ledger' && !loadedTabs.value.accident.ledger && accidentLedgerRef.value) {
      accidentLedgerRef.value.loadAccidents()
      loadedTabs.value.accident.ledger = true
    }
  }
}

// 事故录入完成后跳转到台账
const gotoLedger = () => {
  currentTab.value.accident = 'ledger'
  loadedTabs.value.accident.ledger = false  // 强制重新加载
  switchTab('ledger')
}

// 监听预览状态
const onPreviewStateChanged = (val) => {
  filePreviewVisible.value = val
}

// 初始化：检查上次选择的系统
onMounted(() => {
  const saved = localStorage.getItem('ehs_system')
  if (saved) {
    currentSystem.value = saved
  }
})
</script>

<template>
  <!-- 平台入口页面 -->
  <PlatformEntry v-if="!currentSystem" @select="selectSystem" />

  <!-- ISO审核系统 -->
  <div v-show="currentSystem === 'audit'" :class="filePreviewVisible ? 'full-screen' : ''">
    <!-- 头部 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-4">
        <button @click="backToPlatform" class="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 font-medium">
          ← 返回平台
        </button>
        <h1 class="text-2xl font-bold text-blue-800">ISO 体系智能审核系统</h1>
      </div>
    </div>

    <!-- 标签页切换 -->
    <div class="flex justify-center space-x-4 mb-6">
      <button
        @click="switchTab('workspace')"
        :class="currentTab.audit === 'workspace' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        🚀 审核工作台
      </button>
      <button
        @click="switchTab('report_center')"
        :class="currentTab.audit === 'report_center' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        📁 报告中心
      </button>
      <button
        @click="switchTab('config')"
        :class="currentTab.audit === 'config' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        ⚙️ 引擎配置
      </button>
    </div>

    <!-- 内容区域 -->
    <div v-show="currentTab.audit === 'workspace'">
      <WorkSpace />
    </div>
    <div v-show="currentTab.audit === 'report_center'">
      <ReportCenter ref="reportCenterRef" @previewStateChanged="onPreviewStateChanged" />
    </div>
    <div v-show="currentTab.audit === 'config'">
      <AuditConfig ref="auditConfigRef" />
    </div>
  </div>

  <!-- 事故分析系统 -->
  <div v-show="currentSystem === 'accident'">
    <!-- 头部 -->
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-4">
        <button @click="backToPlatform" class="px-4 py-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 font-medium">
          ← 返回平台
        </button>
        <h1 class="text-2xl font-bold text-orange-800">事故分析系统</h1>
      </div>
    </div>

    <!-- 标签页切换 -->
    <div class="flex justify-center space-x-4 mb-6">
      <button
        @click="switchTab('upload')"
        :class="currentTab.accident === 'upload' ? 'bg-orange-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        📝 事故录入
      </button>
      <button
        @click="switchTab('ledger')"
        :class="currentTab.accident === 'ledger' ? 'bg-orange-600 text-white shadow-md' : 'bg-white text-gray-600 hover:bg-gray-100 border'"
        class="px-6 py-2 rounded-lg font-bold transition-colors"
      >
        📋 事故台账
      </button>
    </div>

    <!-- 内容区域 -->
    <div v-show="currentTab.accident === 'upload'">
      <AccidentUpload ref="accidentUploadRef" @saved="() => {}" @gotoLedger="gotoLedger" />
    </div>
    <div v-show="currentTab.accident === 'ledger'">
      <AccidentLedger ref="accidentLedgerRef" />
    </div>
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