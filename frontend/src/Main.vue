<script setup>
import { ref, onMounted } from 'vue'

// 状态管理
const currentTab = ref('workspace')
const auditMode = ref('standard')
const majorElement = ref('8.1要素')
const fileQueue = ref([])

const isLoading = ref(false)
const queueRemaining = ref(0)

const currentResults = ref([])
const batchSummary = ref({ total: 0, pass: 0, rate: 0 })
const historyReports = ref([])

const previewModalVisible = ref(false)
const currentPreviewReport = ref(null)
const elementStats = ref([]) // 要素统计信息

// 文件预览状态
const filePreviewModalVisible = ref(false)
const currentPreviewFileType = ref('') // loading, docx, pdf, img, xdoc
const currentPreviewUrl = ref('')
const currentPreviewRawUrl = ref('')
const currentPreviewFileName = ref('')

// 切换标签页
const switchTab = (tab) => {
  currentTab.value = tab
  if (tab === 'report_center') fetchReports()
  if (tab === 'admin') {
    fetchPrompts()
    fetchDictionary()
  }
}

// --- 后台管理状态 ---
const systemPrompts = ref([])
const dictionaryJson = ref('')
const aiOptimizerVisible = ref({})
const auditIssuesFeedback = ref({})
const isOptimizing = ref(false)

// --- 管理后台接口方法 ---
const fetchPrompts = async () => {
  const res = await fetch('/api/admin/prompts')
  const data = await res.json()
  if (data.status === 'success') {
    systemPrompts.value = data.data.map(p => ({ ...p, isExpanded: false, isEditing: false, tempContent: p.content }))
  }
}

const savePrompt = async (prompt) => {
  await fetch(`/api/admin/prompts/${prompt.prompt_key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: prompt.tempContent })
  })
  prompt.content = prompt.tempContent
  prompt.isEditing = false
  alert('提示词保存成功！')
}

const aiImprovePrompt = async (prompt) => {
  const feedback = auditIssuesFeedback.value[prompt.prompt_key]
  if (!feedback) return alert('请输入你在审核中遇到的问题或改进期望')

  isOptimizing.value = true
  try {
    const res = await fetch('/api/admin/prompts/improve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_prompt: prompt.tempContent,
        issues_feedback: feedback
      })
    })
    const data = await res.json()
    if (data.status === 'success') {
      prompt.tempContent = data.data.optimized_prompt
      alert('大模型已为您重写了提示词，请检查无误后点击保存！')
    }
  } catch (e) {
    alert('AI 优化失败: ' + e.message)
  } finally {
    isOptimizing.value = false
  }
}

const fetchDictionary = async () => {
  const res = await fetch('/api/admin/dictionary')
  const data = await res.json()
  if (data.status === 'success') {
    dictionaryJson.value = JSON.stringify(data.data, null, 2)
  }
}

const saveDictionary = async () => {
  try {
    const parsed = JSON.parse(dictionaryJson.value)
    await fetch('/api/admin/dictionary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed)
    })
    alert('匹配字典已更新生效！')
  } catch (e) {
    alert('JSON 格式有误，请检查标点符号是否配对！')
  }
}

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

  // 倒数计数器：直接等于文件的总数
  queueRemaining.value = fileQueue.value.length

  let allItems = []
  let passCount = 0

  try {
    // 放弃按要素打包！改为真正地把队列里的文件，一个一个发给后端
    for (const item of fileQueue.value) {
      const formData = new FormData()
      formData.append('audit_mode', item.mode)
      formData.append('major_element', item.element)
      // 每次请求只装载这 1 个文件
      formData.append('files', item.file)

      try {
        const response = await fetch('/api/audit', { method: 'POST', body: formData })
        const resData = await response.json()

        if (resData.status === 'success' && resData.data.length > 0) {
          // 取出这 1 个文件的处理结果
          const result = resData.data[0]
          result.showOriginal = false

          allItems.push(result)
          if (result.是否符合) passCount++

          // 【超棒的UX提升】：实时推送到前端数组，页面上会一个接一个地蹦出报告！
          currentResults.value = [...allItems]

          // 实时更新顶部统计面板
          const currentTotal = allItems.length
          const currentRate = currentTotal > 0 ? ((passCount / currentTotal) * 100).toFixed(2) : 0
          batchSummary.value = { total: currentTotal, pass: passCount, rate: currentRate }
        } else {
          console.error('该文件后端返回错误或为空:', resData)
        }
      } catch (error) {
        console.error(`文件 [${item.name}] 处理网络异常:`, error)
      }

      // 处理完一个，剩余数字减一
      queueRemaining.value--
    }

    // ===== 所有文件全部跑完后的收尾工作 =====
    const finalTotal = allItems.length
    const finalRate = finalTotal > 0 ? ((passCount / finalTotal) * 100).toFixed(2) : 0

    // 依然保留美观的分类排序逻辑
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

    // 所有单件全部算完后，统一将它们作为"一个综合批次"存入数据库
    if (finalTotal > 0) {
      const batchName = allItems[0].文件名 + (finalTotal > 1 ? ` 等 ${finalTotal} 份文件批次` : '')
      const saveRes = await fetch('/api/reports/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_name: batchName,
          total_count: finalTotal,
          pass_count: passCount,
          pass_rate: parseFloat(finalRate),
          details: allItems
        })
      })
      if (!saveRes.ok) console.error('保存综合报告失败')
    }
  } catch (globalError) {
    console.error('整体批处理发生异常:', globalError)
    alert('执行过程中出现严重异常，请检查网络或刷新重试。')
  } finally {
    // 无论如何，清空队列并恢复按钮状态
    fileQueue.value = []
    isLoading.value = false
  }
}

// 获取报告列表
const fetchReports = async () => {
  try {
    const res = await fetch('/api/reports')
    const data = await res.json()
    if (data.status === 'success') historyReports.value = data.data
  } catch (e) {
    console.error('获取报告失败', e)
  }
}

// 删除报告
const deleteReport = async (id) => {
  if (!confirm('确定删除这份报告？')) return

  // 本地立即删除，提升响应速度
  const originalReports = [...historyReports.value]
  historyReports.value = historyReports.value.filter(r => r.id !== id)

  try {
    await fetch(`/api/reports/${id}`, { method: 'DELETE' })
  } catch (e) {
    // 删除失败，回滚
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

  // 计算每个要素的统计数据
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

  // 排序：按文件总数降序
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
const exportWord = (id) => {
  window.open(`/api/reports/export/word/${id}`, '_blank')
}

// 导出 PDF
const exportPDFFromModal = () => {
  const reportId = currentPreviewReport.value?.id
  if (!reportId) {
    alert('无法获取报告ID')
    return
  }
  // 使用后端导出 PDF（类似 Word 导出方式）
  window.open(`/api/reports/export/pdf/${reportId}`, '_blank')
}

// 初始化
onMounted(() => {
  fetchReports()
})
</script>

<template>
  <div :class="filePreviewModalVisible ? 'full-screen' : ''">
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
    <div v-if="currentTab === 'workspace'">
      <!-- 配置区域 -->
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
              <option value="4.1要素">4.1要素</option>
              <option value="4.2要素">4.2要素</option>
              <option value="5.1要素">5.1要素</option>
              <option value="5.2要素">5.2要素</option>
              <option value="5.3要素">5.3要素</option>
              <option value="6.1.1要素">6.1.1要素</option>
              <option value="6.1.2要素">6.1.2要素</option>
              <option value="6.1.3要素">6.1.3要素</option>
              <option value="6.2要素">6.2要素</option>
              <option value="7.1要素">7.1要素</option>
              <option value="7.2要素">7.2要素</option>
              <option value="7.4要素">7.4要素</option>
              <option value="7.5要素">7.5要素</option>
              <option value="8.1要素">8.1要素</option>
              <option value="8.2要素">8.2要素</option>
              <option value="9.1.1要素">9.1.1要素</option>
              <option value="9.1.2要素">9.1.2要素</option>
              <option value="9.2要素">9.2要素</option>
              <option value="9.3要素">9.3要素</option>
              <option value="10.2要素">10.2要素</option>
              <option value="10.3要素">10.3要素</option>
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
    </div>

    <!-- 报告中心 -->
    <div v-if="currentTab === 'report_center'" class="bg-white p-6 rounded-lg shadow-md relative">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-800">📁 历史综合报告库</h2>
        <button @click="fetchReports" class="text-blue-600 font-semibold">🔄 刷新列表</button>
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
                <button @click="deleteReport(report.id)" class="text-red-600 font-bold hover:underline">删除</button>
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
              <button @click="exportWord(currentPreviewReport?.id)" class="px-4 py-2 bg-blue-600 text-white rounded font-bold shadow hover:bg-blue-700">
                导Word
              </button>
              <button @click="exportPDFFromModal" class="px-4 py-2 bg-green-600 text-white rounded font-bold shadow hover:bg-green-700">
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

    <!-- 引擎配置中台 -->
    <div v-if="currentTab === 'admin'" class="space-y-8">
      <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-indigo-500">
        <h2 class="text-2xl font-bold text-gray-800 mb-6">🧠 核心审核大模型 Prompt 管理</h2>
        <p class="text-sm text-gray-500 mb-4">通过调优提示词，可以直接改变 AI 判罚的尺度和侧重点。所有变量（如 {standard_text}）请务必保留。</p>

        <div class="space-y-4">
          <div v-for="prompt in systemPrompts" :key="prompt.prompt_key" class="border rounded-lg overflow-hidden">
            <div
              @click="prompt.isExpanded = !prompt.isExpanded"
              class="bg-gray-50 p-4 cursor-pointer hover:bg-gray-100 flex justify-between items-center transition-colors"
            >
              <div>
                <span class="font-bold text-lg text-indigo-900">{{ prompt.prompt_name }}</span>
                <span class="ml-4 text-xs text-gray-400">最后更新: {{ prompt.updated_at }}</span>
              </div>
              <svg class="w-6 h-6 transform transition-transform" :class="prompt.isExpanded ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>

            <div v-show="prompt.isExpanded" class="p-4 bg-white border-t">
              <div v-if="!prompt.isEditing" class="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm whitespace-pre-wrap leading-relaxed">
                {{ prompt.content }}
              </div>
              <textarea
                v-else
                v-model="prompt.tempContent"
                class="w-full h-64 p-4 border-2 border-indigo-300 rounded-md font-mono text-sm focus:ring focus:ring-indigo-200 outline-none"
              ></textarea>

              <div class="mt-4 flex justify-between items-center">
                <div class="space-x-3">
                  <button v-if="!prompt.isEditing" @click="prompt.isEditing = true" class="px-4 py-2 bg-indigo-100 text-indigo-700 font-bold rounded hover:bg-indigo-200">编辑提示词</button>
                  <template v-else>
                    <button @click="savePrompt(prompt)" class="px-4 py-2 bg-green-600 text-white font-bold rounded hover:bg-green-700 shadow-sm">💾 保存生效</button>
                    <button @click="prompt.isEditing = false; prompt.tempContent = prompt.content" class="px-4 py-2 bg-gray-200 text-gray-700 font-bold rounded hover:bg-gray-300">取消</button>
                  </template>
                </div>

                <button
                  v-if="prompt.isEditing"
                  @click="aiOptimizerVisible[prompt.prompt_key] = !aiOptimizerVisible[prompt.prompt_key]"
                  class="text-sm font-bold flex items-center"
                  :class="aiOptimizerVisible[prompt.prompt_key] ? 'text-orange-600' : 'text-blue-600'"
                >
                  ✨ {{ aiOptimizerVisible[prompt.prompt_key] ? '收起 AI 助理' : 'AI 辅助重写提示词' }}
                </button>
              </div>

              <div v-show="aiOptimizerVisible[prompt.prompt_key] && prompt.isEditing" class="mt-6 bg-gradient-to-r from-blue-50 to-indigo-50 p-5 rounded-lg border border-blue-100">
                <label class="block font-bold text-blue-900 mb-2">🎯 告诉 AI 你遇到了什么审核问题？</label>
                <textarea
                  v-model="auditIssuesFeedback[prompt.prompt_key]"
                  placeholder="例如：最近AI总是对签字未填写的判罚太严，或者对环保台账的数字计算不准，请帮我调整提示词让它更关注本质合规..."
                  class="w-full h-24 p-3 border border-blue-200 rounded text-sm mb-3 focus:ring-2 focus:ring-blue-300 outline-none"
                ></textarea>
                <button
                  @click="aiImprovePrompt(prompt)"
                  :disabled="isOptimizing"
                  class="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded shadow hover:shadow-lg disabled:opacity-50 flex items-center"
                >
                  <svg v-if="isOptimizing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  {{ isOptimizing ? '大模型深度思考重写中...' : '开始重写提示词' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-green-500">
        <div class="flex justify-between items-center mb-6">
          <div>
            <h2 class="text-2xl font-bold text-gray-800">📂 体系条款与文件匹配字典</h2>
            <p class="text-sm text-gray-500 mt-1">全局路由配置 `element_routing_dictionary_final.json`，修改后立即生效。</p>
          </div>
          <button @click="saveDictionary" class="px-6 py-2 bg-green-600 text-white font-bold rounded shadow hover:bg-green-700">
            保存字典配置
          </button>
        </div>
        <div class="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4 text-sm text-yellow-800">
          ⚠️ 注意：请确保遵循严格的 JSON 格式（双引号、逗号不可缺少），格式错误将无法保存。
        </div>
        <textarea
          v-model="dictionaryJson"
          class="w-full h-96 p-4 bg-gray-50 border border-gray-300 rounded font-mono text-sm leading-relaxed focus:border-green-400 focus:ring-1 focus:ring-green-400 outline-none"
          spellcheck="false"
        ></textarea>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles - can be extended as needed */
</style>
