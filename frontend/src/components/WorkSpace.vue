<script setup>
import { ref } from 'vue'
import { submitAuditSingle, saveReport } from '../api/audit.js'

// 审核配置状态
const auditMode = ref('standard')
const majorElement = ref('8.1要素')

// 文件队列状态
const fileQueue = ref([])
const isLoading = ref(false)
const queueRemaining = ref(0)

// 审核结果状态
const currentResults = ref([])
const batchSummary = ref({ total: 0, pass: 0, rate: 0 })

// 要素选项列表
const elementOptions = [
  '4.1要素', '4.2要素', '5.1要素', '5.2要素', '5.3要素',
  '6.1.1要素', '6.1.2要素', '6.1.3要素', '6.2要素',
  '7.1要素', '7.2要素', '7.4要素', '7.5要素',
  '8.1要素', '8.2要素',
  '9.1.1要素', '9.1.2要素', '9.2要素', '9.3要素',
  '10.2要素', '10.3要素'
]

// 文件上传处理
const handleFileUpload = (event) => {
  const selectedFiles = Array.from(event.target.files)
  selectedFiles.forEach(file => {
    fileQueue.value.push({
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      file: file,
      name: file.name,
      mode: auditMode.value,
      element: majorElement.value,
      elementName: auditMode.value === 'standard' ? majorElement.value : '日常检查'
    })
  })
  event.target.value = ''
}

// 移除文件
const removeFile = (id) => {
  fileQueue.value = fileQueue.value.filter(item => item.id !== id)
}

// 清空队列
const clearQueue = () => {
  fileQueue.value = []
}

// 提交审核 - 流水线单件发货模式
const submitAudit = async () => {
  if (fileQueue.value.length === 0) return

  isLoading.value = true
  currentResults.value = []
  batchSummary.value = { total: 0, pass: 0, rate: 0 }

  queueRemaining.value = fileQueue.value.length

  let allItems = []
  let passCount = 0

  try {
    for (const item of fileQueue.value) {
      const formData = new FormData()
      formData.append('audit_mode', item.mode)
      formData.append('major_element', item.element)
      formData.append('files', item.file)

      try {
        const resData = await submitAuditSingle(formData)

        if (resData.status === 'success' && resData.data.length > 0) {
          const result = resData.data[0]
          result.showOriginal = false

          allItems.push(result)
          if (result.是否符合) passCount++

          // 实时推送到前端
          currentResults.value = [...allItems]

          // 实时更新统计
          const currentTotal = allItems.length
          const currentRate = currentTotal > 0 ? ((passCount / currentTotal) * 100).toFixed(2) : 0
          batchSummary.value = { total: currentTotal, pass: passCount, rate: currentRate }
        } else {
          console.error('该文件后端返回错误或为空:', resData)
        }
      } catch (error) {
        console.error(`文件 [${item.name}] 处理网络异常:`, error)
      }

      queueRemaining.value--
    }

    // 最终排序
    const conclusionOrder = { '符合': 1, '部分符合': 2, '不符合': 3 }
    allItems.sort((a, b) => {
      const resA = a.审核结果 || {}
      const resB = b.审核结果 || {}
      const concA = conclusionOrder[resA.结论] || 4
      const concB = conclusionOrder[resB.结论] || 4
      if (concA !== concB) return concA - concB
      const elemA = a.要素 || ''
      const elemB = b.要素 || ''
      return elemA.localeCompare(elemB)
    })

    currentResults.value = allItems

    // 保存综合报告
    const finalTotal = allItems.length
    const finalRate = finalTotal > 0 ? ((passCount / finalTotal) * 100).toFixed(2) : 0
    if (finalTotal > 0) {
      const batchName = allItems[0].文件名 + (finalTotal > 1 ? ` 等 ${finalTotal} 份文件批次` : '')
      await saveReport(batchName, finalTotal, passCount, parseFloat(finalRate), allItems)
    }
  } catch (globalError) {
    console.error('整体批处理发生异常:', globalError)
    alert('执行过程中出现严重异常，请检查网络或刷新重试。')
  } finally {
    fileQueue.value = []
    isLoading.value = false
  }
}
</script>

<template>
  <div class="bg-white p-6 rounded-lg shadow-md mb-8">
    <!-- 审核模式选择 -->
    <div class="mb-6 border-b border-gray-200 pb-6">
      <label class="block text-base font-bold text-gray-800 mb-4">⚙️ 步骤 1: 选择系统运行模式</label>
      <div class="flex flex-wrap gap-4">
        <label
          class="flex items-center cursor-pointer px-5 py-3 rounded-lg border transition-colors"
          :class="auditMode === 'standard' ? 'bg-blue-50 border-blue-400 ring-2 ring-blue-200' : 'bg-gray-50 border-gray-200'"
        >
          <input type="radio" v-model="auditMode" value="standard" class="hidden" />
          <span class="font-bold text-gray-700">标准体系交叉审核</span>
        </label>
        <label
          class="flex items-center cursor-pointer px-5 py-3 rounded-lg border transition-colors"
          :class="auditMode === 'daily_inspection' ? 'bg-green-50 border-green-400 ring-2 ring-green-200' : 'bg-gray-50 border-gray-200'"
        >
          <input type="radio" v-model="auditMode" value="daily_inspection" class="hidden" />
          <span class="font-bold text-gray-700">日常检查台账分析</span>
        </label>
      </div>
    </div>

    <!-- 要素选择和文件上传 -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div v-if="auditMode === 'standard'">
        <label class="block text-sm font-medium text-gray-700 mb-2">步骤 2: 锁定对应的大要素环境</label>
        <select v-model="majorElement" class="block w-full rounded-md border-gray-300 p-2 border">
          <option v-for="opt in elementOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </div>
      <div
        v-if="auditMode === 'daily_inspection'"
        class="bg-green-50 p-4 rounded-md border border-green-200 flex items-center"
      >
        <p class="text-sm text-green-800">
          💡 日常检查台账将统一归入 <strong>8.1要素</strong>，由大模型结合8.1主要素原文进行指导，并默认计入"符合"率。
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">步骤 3: 叠加文件入列</label>
        <input
          type="file"
          multiple
          accept=".doc,.docx,.pdf,.xlsx,.csv,.jpg,.png"
          @change="handleFileUpload"
          class="block w-full border p-1 rounded-md cursor-pointer"
        />
      </div>
    </div>

    <!-- 文件队列 -->
    <div v-if="fileQueue.length > 0" class="mt-8 pt-6 border-t border-gray-200">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold text-gray-800">
          📥 待批处理队列
          <span class="bg-blue-100 text-blue-800 py-1 px-3 rounded-full text-sm">共 {{ fileQueue.length }} 个文件</span>
        </h3>
        <button @click="clearQueue" class="text-sm text-red-500 font-semibold">清空队列</button>
      </div>
      <ul class="space-y-3 max-h-60 overflow-y-auto pr-2">
        <li
          v-for="item in fileQueue"
          :key="item.id"
          class="flex justify-between items-center bg-gray-50 p-3 rounded-lg border"
        >
          <span class="font-medium text-gray-800">{{ item.name }}</span>
          <div class="flex items-center space-x-2">
            <span class="text-xs px-2 py-1 bg-gray-200 rounded">{{ item.elementName }}</span>
            <button @click="removeFile(item.id)" class="text-red-500 font-bold px-2">×</button>
          </div>
        </li>
      </ul>
    </div>

    <!-- 提交按钮 -->
    <div class="mt-8 flex justify-center">
      <button
        @click="submitAudit"
        :disabled="isLoading || fileQueue.length === 0"
        class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg shadow disabled:opacity-50 text-lg"
      >
        {{ isLoading ? `智能审阅中 (剩余 ${queueRemaining} 组)...` : '🚀 开始执行本次综合审核' }}
      </button>
    </div>
  </div>

  <!-- 审核结果 -->
  <div id="pdf-content-workspace" v-if="currentResults.length > 0" class="space-y-6 bg-white p-8 rounded-lg shadow-sm">
    <div class="bg-blue-50 p-4 rounded-lg mb-4 flex justify-between items-center border border-blue-200">
      <div>
        <h2 class="text-xl font-bold text-blue-800">📊 本次综合审核结果</h2>
        <p class="text-sm mt-1">
          共检测 <strong>{{ batchSummary.total }}</strong> 个文件，整体符合率：
          <span class="font-bold text-green-600">{{ batchSummary.rate }}%</span>
        </p>
      </div>
    </div>

    <div
      v-for="(item, index) in currentResults"
      :key="index"
      class="bg-white rounded-lg border-l-8 mb-6 p-5 border border-gray-100 shadow-sm"
      :class="item.是否符合 ? 'border-green-500' : 'border-red-500'"
    >
      <div class="flex justify-between mb-2">
        <h3 class="text-lg font-bold">
          🄿 {{ item.文件名 }}
          <span class="text-xs text-gray-500 ml-2">({{ item.要素 }})</span>
        </h3>
        <span class="px-3 py-1 rounded bg-gray-100 text-sm font-bold">{{ item.审核结果.结论 }}</span>
      </div>
      <p class="text-sm text-blue-600 font-semibold mb-4">
        📍 审核依据:
        <span class="text-gray-700 font-normal">{{ item.审核文件 }}</span>
      </p>

      <div class="grid gap-3 text-sm">
        <div class="bg-orange-50 p-3 rounded">
          <strong>🧠 问题剖析:</strong>
          {{ item.审核结果.逻辑缺陷描述 }}
        </div>
        <div class="bg-gray-50 p-3 rounded border">
          <strong>📖 引用依据:</strong>
          {{ item.审核结果.引用依据 }}
        </div>
        <div class="bg-green-50 p-3 rounded">
          <strong>💡 修改建议:</strong>
          {{ item.审核结果.修改意见 }}
        </div>
      </div>
    </div>
  </div>
</template>