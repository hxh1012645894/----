<script setup>
import { ref, onMounted, watch } from 'vue'
import { fetchReports, deleteReport, exportWord, exportPDF } from '../api/report.js'

// 报告列表状态
const historyReports = ref([])

// 报告预览状态
const previewModalVisible = ref(false)
const currentPreviewReport = ref(null)
const elementStats = ref([])

// 文件预览状态
const filePreviewModalVisible = ref(false)
const currentPreviewFileType = ref('')
const currentPreviewUrl = ref('')
const currentPreviewRawUrl = ref('')
const currentPreviewFileName = ref('')

// 加载报告列表
const loadReports = async () => {
  try {
    const data = await fetchReports()
    if (data.status === 'success') historyReports.value = data.data
  } catch (e) {
    console.error('获取报告失败', e)
  }
}

// 删除报告
const handleDeleteReport = async (id) => {
  if (!confirm('确定删除这份报告？')) return

  const originalReports = [...historyReports.value]
  historyReports.value = historyReports.value.filter(r => r.id !== id)

  try {
    await deleteReport(id)
  } catch (e) {
    historyReports.value = originalReports
    alert('删除失败: ' + e.message)
  }
}

// 打开报告预览
const openPreview = (report) => {
  let details = []
  try {
    details = JSON.parse(report.details_json)
    details.forEach(d => (d.showOriginal = false))

    const conclusionOrder = { '符合': 1, '部分符合': 2, '不符合': 3 }
    details.sort((a, b) => {
      const resA = a.审核结果 || {}
      const resB = b.审核结果 || {}
      const concA = conclusionOrder[resA.结论] || 4
      const concB = conclusionOrder[resB.结论] || 4
      if (concA !== concB) return concA - concB
      const elemA = a.要素 || ''
      const elemB = b.要素 || ''
      return elemA.localeCompare(elemB)
    })
  } catch (e) {
    console.error('解析详情失败', e)
  }

  // 计算要素统计
  const elementStatsMap = {}
  details.forEach(item => {
    const element = item.要素 || '未知要素'
    if (!elementStatsMap[element]) {
      elementStatsMap[element] = { element, total: 0, pass: 0, fail: 0, rate: 0 }
    }
    elementStatsMap[element].total += 1
    if (item.是否符合 === true) {
      elementStatsMap[element].pass += 1
    } else {
      elementStatsMap[element].fail += 1
    }
    elementStatsMap[element].rate = ((elementStatsMap[element].pass / elementStatsMap[element].total) * 100).toFixed(2)
  })

  elementStats.value = Object.values(elementStatsMap).sort((a, b) => b.total - a.total)
  currentPreviewReport.value = { ...report, details: details }
  previewModalVisible.value = true
}

// 打开原始文件预览
const openOriginalFile = (relativePath, filename) => {
  const fullPublicUrl = window.location.origin + relativePath
  currentPreviewRawUrl.value = fullPublicUrl
  currentPreviewFileName.value = filename

  filePreviewModalVisible.value = true
  currentPreviewFileType.value = 'loading'

  const ext = filename.split('.').pop().toLowerCase()

  if (ext === 'pdf') {
    currentPreviewFileType.value = 'pdf'
  } else if (['jpg', 'jpeg', 'png'].includes(ext)) {
    currentPreviewFileType.value = 'img'
  } else if (ext === 'docx') {
    setTimeout(() => {
      fetch(fullPublicUrl)
        .then(res => res.blob())
        .then(blob => {
          const container = document.getElementById('docx-container')
          if (container) {
            container.innerHTML = ''
            docx.renderAsync(blob, container).then(() => {
              currentPreviewFileType.value = 'docx'
            })
          }
        })
        .catch(e => {
          console.error('DOCX 渲染失败，降级给 XDOC', e)
          currentPreviewUrl.value = 'https://view.xdocin.com/view?src=' + encodeURIComponent(fullPublicUrl)
          currentPreviewFileType.value = 'xdoc'
        })
    }, 100)
  } else {
    currentPreviewUrl.value = 'https://view.xdocin.com/view?src=' + encodeURIComponent(fullPublicUrl)
    currentPreviewFileType.value = 'xdoc'
  }
}

// 导出 Word
const handleExportWord = (id) => {
  exportWord(id)
}

// 导出 PDF
const handleExportPDF = () => {
  const reportId = currentPreviewReport.value?.id
  if (!reportId) {
    alert('无法获取报告ID')
    return
  }
  exportPDF(reportId)
}

// 暴露给父组件的方法
defineExpose({
  loadReports
})

// 监听预览状态，同步到父组件
const emit = defineEmits(['previewStateChanged'])
watch(filePreviewModalVisible, (val) => {
  emit('previewStateChanged', val)
})

onMounted(() => {
  loadReports()
})
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow-md relative">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">📁 历史综合报告库</h2>
      <button @click="loadReports" class="text-blue-600 font-semibold">🔄 刷新列表</button>
    </div>

    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200 border">
        <thead class="bg-gray-50 text-xs font-medium text-gray-500 uppercase">
          <tr>
            <th class="px-6 py-3 text-left">报告批次名</th>
            <th class="px-6 py-3 text-left">文件总数</th>
            <th class="px-6 py-3 text-left">综合符合率</th>
            <th class="px-6 py-3 text-left">生成时间</th>
            <th class="px-6 py-3 text-right">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200 text-sm">
          <tr v-for="report in historyReports" :key="report.id" class="hover:bg-gray-50">
            <td class="px-6 py-4 font-medium text-gray-900">{{ report.batch_name }}</td>
            <td class="px-6 py-4">{{ report.total_count }} 份</td>
            <td class="px-6 py-4 font-bold" :class="report.pass_rate >= 80 ? 'text-green-600' : 'text-red-600'">
              {{ report.pass_rate }}%
            </td>
            <td class="px-6 py-4 text-gray-500">{{ report.created_at }}</td>
            <td class="px-6 py-4 text-right space-x-3">
              <button @click="openPreview(report)" class="text-blue-600 font-bold hover:underline">详情</button>
              <button @click="handleDeleteReport(report.id)" class="text-red-600 font-bold hover:underline">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 报告预览模态框 -->
    <div
      v-if="previewModalVisible"
      class="fixed inset-0 flex items-start z-40 p-4 transition-all duration-500 ease-in-out pointer-events-none"
      :class="filePreviewModalVisible ? 'justify-start bg-transparent' : 'justify-center bg-black bg-opacity-60 pointer-events-auto'"
    >
      <div
        class="bg-white rounded-lg flex flex-col shadow-2xl overflow-hidden transition-all duration-500 pointer-events-auto"
        :class="filePreviewModalVisible ? 'w-[48%] h-[95vh] border-2 border-blue-200' : 'w-full max-w-5xl max-h-[90vh] mt-10'"
      >
        <div class="p-4 border-b flex justify-between items-center bg-gray-50">
          <h2 class="text-xl font-bold text-gray-800">📄 报告明细 - {{ currentPreviewReport?.batch_name }}</h2>
          <div class="space-x-3 shrink-0">
            <button @click="handleExportWord(currentPreviewReport?.id)" class="px-4 py-2 bg-blue-600 text-white rounded font-bold shadow hover:bg-blue-700">
              导Word
            </button>
            <button @click="handleExportPDF" class="px-4 py-2 bg-green-600 text-white rounded font-bold shadow hover:bg-green-700">
              导PDF
            </button>
            <button @click="previewModalVisible = false" class="px-4 py-2 bg-gray-300 text-gray-800 rounded font-bold hover:bg-gray-400">
              关闭
            </button>
          </div>
        </div>

        <div class="p-6 overflow-y-auto flex-1 bg-gray-100">
          <div id="modal-pdf-content" class="bg-white p-8 rounded shadow-sm max-w-4xl mx-auto">
            <div class="text-center mb-8 border-b pb-4">
              <h1 class="text-3xl font-bold text-gray-800 mb-2">ISO 体系综合审核报告</h1>
              <p class="text-gray-500">报告生成时间: {{ currentPreviewReport?.created_at }}</p>
              <div class="mt-4 flex justify-center space-x-6 text-lg">
                <span>总文件数: <strong>{{ currentPreviewReport?.total_count }}</strong></span>
                <span>符合数: <strong>{{ currentPreviewReport?.pass_count }}</strong></span>
                <span
                  :class="currentPreviewReport?.pass_rate >= 80 ? 'text-green-600' : 'text-red-600'"
                  class="font-bold"
                >
                  符合率: {{ currentPreviewReport?.pass_rate }}%
                </span>
              </div>
            </div>

            <!-- 要素统计表格 -->
            <div v-if="elementStats.length > 0" class="mb-6 border-l-4 border-blue-500 pl-4 bg-white">
              <h3 class="text-xl font-bold mb-3">各要素审核统计</h3>
              <table class="min-w-full border text-sm text-left">
                <thead class="bg-gray-50 text-xs font-medium text-gray-500 uppercase">
                  <tr>
                    <th class="px-3 py-2 border-r">要素名称</th>
                    <th class="px-3 py-2 border-r">文件总数</th>
                    <th class="px-3 py-2 border-r">符合数量</th>
                    <th class="px-3 py-2 border-r">不符合数量</th>
                    <th class="px-3 py-2">符合率</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200 text-sm">
                  <tr v-for="(stat, index) in elementStats" :key="index" class="hover:bg-gray-50">
                    <td class="px-3 py-2 border-r font-medium">{{ stat.element }}</td>
                    <td class="px-3 py-2 border-r">{{ stat.total }}</td>
                    <td class="px-3 py-2 border-r text-green-600">{{ stat.pass }}</td>
                    <td class="px-3 py-2 border-r text-red-600">{{ stat.fail }}</td>
                    <td class="px-3 py-2 font-bold" :class="stat.rate >= 80 ? 'text-green-600' : 'text-red-600'">{{ stat.rate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-for="(item, idx) in currentPreviewReport?.details" :key="idx" class="mb-8 border-l-4 border-blue-500 pl-4 bg-white">
              <h3 class="text-xl font-bold mb-2">{{ idx + 1 }}. {{ item.文件名 }}</h3>
              <p class="text-sm text-gray-600 mb-4">
                执行要素: {{ item.要素 }} | 判定依据: {{ item.审核文件 }}
              </p>

              <table class="min-w-full border text-sm text-left">
                <tbody>
                  <tr class="border-b">
                    <th class="w-32 bg-gray-50 p-2 border-r">审核结论</th>
                    <td class="p-2 font-bold" :class="item.审核结果.结论 === '符合' ? 'text-green-600' : 'text-red-600'">
                      {{ item.审核结果.结论 }}
                    </td>
                  </tr>
                  <tr class="border-b">
                    <th class="bg-gray-50 p-2 border-r">问题剖析</th>
                    <td class="p-2 whitespace-pre-wrap">{{ item.审核结果.逻辑缺陷描述 }}</td>
                  </tr>
                  <tr class="border-b">
                    <th class="bg-gray-50 p-2 border-r">引用依据</th>
                    <td class="p-2">{{ item.审核结果.引用依据 }}</td>
                  </tr>
                  <tr>
                    <th class="bg-gray-50 p-2 border-r">整改建议</th>
                    <td class="p-2 whitespace-pre-wrap text-blue-700">{{ item.审核结果.修改意见 }}</td>
                  </tr>
                </tbody>
              </table>

              <div class="mt-3 flex flex-wrap gap-4" data-html2canvas-ignore="true">
                <button
                  @click="item.showOriginal = !item.showOriginal"
                  class="text-xs text-blue-600 hover:text-blue-800 font-bold flex items-center transition-colors"
                >
                  <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  </svg>
                  {{ item.showOriginal ? '收起系统提取原文' : '🔍 查看系统提取原文 (溯源核对)' }}
                </button>

                <button
                  v-if="item.原文件在线地址"
                  @click="openOriginalFile(item.原文件在线地址, item.文件名)"
                  class="text-xs text-indigo-600 hover:text-indigo-800 font-bold flex items-center transition-colors"
                >
                  👁️ 开启对照分屏预览 (Word/Excel/PDF等)
                </button>
              </div>
              <div
                v-if="item.showOriginal"
                data-html2canvas-ignore="true"
                class="mt-2 p-3 bg-gray-900 text-green-400 font-mono text-xs rounded-lg overflow-y-auto max-h-64 whitespace-pre-wrap shadow-inner leading-relaxed"
              >
                {{ item.原文 || '未提取到文本内容...' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文件对照预览面板 -->
    <div
      class="fixed right-0 top-0 w-[50%] h-full bg-gray-100 shadow-2xl border-l border-gray-300 z-[60] flex flex-col transition-transform duration-500 ease-in-out"
      :class="filePreviewModalVisible ? 'translate-x-0' : 'translate-x-full'"
    >
      <div class="p-3 bg-white border-b flex justify-between items-center shadow-sm">
        <h3 class="font-bold text-lg text-blue-900 truncate pr-4">👀 原件对照：{{ currentPreviewFileName }}</h3>
        <div class="space-x-2 flex items-center shrink-0">
          <a :href="currentPreviewRawUrl" download class="text-blue-600 hover:text-blue-800 text-sm font-bold border border-blue-400 px-3 py-1.5 rounded bg-blue-50">
            ⬇️ 下载原件
          </a>
          <button
            @click="filePreviewModalVisible = false"
            class="bg-red-500 text-white px-4 py-1.5 rounded hover:bg-red-600 font-bold shadow"
          >
            ✖ 关闭对照
          </button>
        </div>
      </div>

      <div class="flex-1 w-full h-full overflow-y-auto bg-gray-200 relative">
        <div v-if="currentPreviewFileType === 'loading'" class="absolute inset-0 flex flex-col items-center justify-center bg-white z-10 text-gray-500">
          <svg class="animate-spin h-10 w-10 text-blue-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="font-bold">极速本地渲染中，请稍候...</span>
        </div>

        <iframe v-if="currentPreviewFileType === 'pdf'" :src="currentPreviewRawUrl" class="w-full h-full border-0 bg-white"></iframe>

        <div v-show="currentPreviewFileType === 'docx'" id="docx-container" class="w-full bg-white min-h-full p-6 shadow-inner"></div>

        <div v-show="currentPreviewFileType === 'img'" class="w-full h-full flex items-center justify-center p-4 bg-white">
          <img :src="currentPreviewRawUrl" class="max-w-full max-h-full shadow-lg border" />
        </div>

        <iframe v-if="currentPreviewFileType === 'xdoc'" :src="currentPreviewUrl" class="w-full h-full border-0 bg-white"></iframe>
      </div>
    </div>
  </div>
</template>