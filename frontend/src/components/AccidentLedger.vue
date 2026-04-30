<script setup>
import { ref, onMounted, nextTick } from 'vue'
import {
  fetchAccidents, fetchAccidentDetail, deleteAccident, submitAccidentForAnalysis,
  fetchMeasures, addMeasure, assignMeasure, completeMeasure, fetchOverdueMeasures,
  checkAndMarkOverdue, updateMeasureStatus,
  fetchAlert, generateAlert, updateAlert, sendAlert,
  fetchTrainings, addTraining, deleteTraining,
  generateLedger, fetchLedgerContent, updateLedgerContent,
  uploadAccidentAttachments
} from '../api/accident.js'
import AccidentForm from './AccidentForm.vue'

// 列表数据
const accidents = ref([])
const overdueMeasures = ref([])

// 消息提示
const message = ref('')
const messageType = ref('success')

// 显示消息
const showMessage = (text, type = 'success') => {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 3000)
}

// 详情弹窗状态
const detailModalVisible = ref(false)
const currentAccident = ref(null)
const isLoading = ref(false)

// 视图模式：list 或 form
const viewMode = ref('list')

// 表单组件引用
const accidentFormRef = ref(null)

// 整改措施面板状态
const measureModalVisible = ref(false)
const currentMeasure = ref(null)
const assignModalVisible = ref(false)
const assignForm = ref({ responsible_person: '', deadline: '' })
const completeModalVisible = ref(false)
const completeFiles = ref([])

// 警示面板状态
const alertModalVisible = ref(false)
const currentAlert = ref(null)
const alertForm = ref({ alert_title: '', alert_content: '' })

// 培训面板状态
const trainingModalVisible = ref(false)
const trainingForm = ref({
  training_date: '',
  training_location: '',
  training_content: '',
  trainer_name: '',
  attendees_count: 0,
  sign_sheet_attachment: '',
  photo_attachments: []
})
const trainingFiles = ref([])

// 台账编辑面板状态
const ledgerEditModalVisible = ref(false)
const ledgerContent = ref({
  basic_info: {},
  analysis: {},
  measures: []
})

// 加载事故列表
const loadAccidents = async () => {
  isLoading.value = true
  try {
    const res = await fetchAccidents()
    if (res.status === 'success') {
      accidents.value = res.data
    }
    // 加载逾期整改
    const overdueRes = await fetchOverdueMeasures()
    if (overdueRes.status === 'success') {
      overdueMeasures.value = overdueRes.data
    }
  } catch (e) {
    console.error('加载事故列表失败', e)
  }
  isLoading.value = false
}

// 检查逾期整改
const checkOverdue = async () => {
  isLoading.value = true
  try {
    const res = await checkAndMarkOverdue()
    if (res.status === 'success') {
      overdueMeasures.value = res.data.overdue_measures
      showMessage(`已标记 ${res.data.marked_count} 条逾期整改措施`)
      loadAccidents()
    }
  } catch (e) {
    showMessage('检查失败', 'error')
  }
  isLoading.value = false
}

// 查看详情
const viewDetail = async (id) => {
  isLoading.value = true
  try {
    const res = await fetchAccidentDetail(id)
    if (res.status === 'success') {
      currentAccident.value = res.data
      detailModalVisible.value = true
    } else {
      showMessage(res.message || '获取详情失败', 'error')
    }
  } catch (e) {
    showMessage('获取详情失败', 'error')
  }
  isLoading.value = false
}

// 删除事故
const handleDelete = async (id) => {
  if (!confirm('确定删除这条事故记录？')) return

  const original = [...accidents.value]
  accidents.value = accidents.value.filter(a => a.id !== id)

  try {
    const res = await deleteAccident(id)
    if (res.status === 'success') {
      showMessage('删除成功')
    } else {
      accidents.value = original
      showMessage(res.message || '删除失败', 'error')
    }
  } catch (e) {
    accidents.value = original
    showMessage('删除失败', 'error')
  }
}

// 重新分析
const reanalyze = async (id) => {
  if (!confirm('确定重新进行AI分析？')) return

  isLoading.value = true
  try {
    const res = await submitAccidentForAnalysis(id)
    if (res.status === 'success') {
      showMessage('AI分析完成')
      const detailRes = await fetchAccidentDetail(id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
    } else {
      showMessage(res.message || '分析失败', 'error')
    }
  } catch (e) {
    showMessage('分析失败', 'error')
  }
  isLoading.value = false
}

// 新建事故
const createNew = async () => {
  viewMode.value = 'form'
  await nextTick()
  if (accidentFormRef.value) {
    accidentFormRef.value.resetForm()
  }
}

// 编辑事故
const editAccident = async (id) => {
  isLoading.value = true
  try {
    const res = await fetchAccidentDetail(id)
    if (res.status === 'success') {
      viewMode.value = 'form'
      await nextTick()
      if (accidentFormRef.value) {
        accidentFormRef.value.loadAccident(res.data)
      }
    }
  } catch (e) {
    showMessage('加载事故数据失败', 'error')
  }
  isLoading.value = false
}

// 返回列表
const backToList = () => {
  viewMode.value = 'list'
  loadAccidents()
}

// 编辑保存成功
const handleSaved = () => {
  showMessage('保存成功')
  backToList()
}

// 关闭详情弹窗
const closeDetailModal = () => {
  detailModalVisible.value = false
  currentAccident.value = null
}

// ==================== 整改措施管理 ====================

// 打开指派弹窗
const openAssignModal = (measure) => {
  currentMeasure.value = measure
  assignForm.value = {
    responsible_person: measure.responsible_person || '',
    deadline: measure.deadline || ''
  }
  assignModalVisible.value = true
}

// 指派责任人
const handleAssign = async () => {
  if (!assignForm.value.responsible_person || !assignForm.value.deadline) {
    showMessage('请填写责任人和整改期限', 'error')
    return
  }
  isLoading.value = true
  try {
    const res = await assignMeasure(currentAccident.value.id, currentMeasure.value.id, assignForm.value)
    if (res.status === 'success') {
      assignModalVisible.value = false
      // 刷新详情
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('指派成功')
    } else {
      showMessage(res.message || '指派失败', 'error')
    }
  } catch (e) {
    showMessage('指派失败', 'error')
  }
  isLoading.value = false
}

// 打开完成弹窗
const openCompleteModal = (measure) => {
  currentMeasure.value = measure
  completeFiles.value = []
  completeModalVisible.value = true
}

// 上传完成附件
const handleCompleteFileUpload = async (event) => {
  const files = Array.from(event.target.files)
  if (files.length === 0) return
  isLoading.value = true
  try {
    const res = await uploadAccidentAttachments(files)
    if (res.status === 'success') {
      completeFiles.value.push(...res.data)
    }
  } catch (e) {
    showMessage('上传失败', 'error')
  }
  isLoading.value = false
}

// 标记完成
const handleComplete = async () => {
  isLoading.value = true
  try {
    const res = await completeMeasure(currentAccident.value.id, currentMeasure.value.id, {
      completion_proof: completeFiles.value
    })
    if (res.status === 'success') {
      completeModalVisible.value = false
      // 刷新详情
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('整改已完成')
    } else {
      showMessage(res.message || '操作失败', 'error')
    }
  } catch (e) {
    showMessage('操作失败', 'error')
  }
  isLoading.value = false
}

// 添加新措施
const handleAddMeasure = async () => {
  const content = prompt('请输入整改措施内容')
  if (!content) return
  isLoading.value = true
  try {
    const res = await addMeasure(currentAccident.value.id, { measure_content: content, measure_order: currentAccident.value.measures.length + 1 })
    if (res.status === 'success') {
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('添加成功')
    } else {
      showMessage(res.message || '添加失败', 'error')
    }
  } catch (e) {
    showMessage('添加失败', 'error')
  }
  isLoading.value = false
}

// ==================== 警示管理 ====================

// 生成警示
const handleGenerateAlert = async () => {
  if (!currentAccident.value.analysis) {
    showMessage('请先进行AI分析', 'error')
    return
  }
  isLoading.value = true
  try {
    const res = await generateAlert(currentAccident.value.id)
    if (res.status === 'success') {
      currentAlert.value = res.data
      alertForm.value = {
        alert_title: res.data.alert_title,
        alert_content: res.data.alert_content
      }
      alertModalVisible.value = true
      // 刷新详情
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
    } else {
      showMessage(res.message || '生成失败', 'error')
    }
  } catch (e) {
    showMessage('生成失败', 'error')
  }
  isLoading.value = false
}

// 编辑警示
const openAlertModal = () => {
  if (currentAccident.value.alert) {
    alertForm.value = {
      alert_title: currentAccident.value.alert.alert_title,
      alert_content: currentAccident.value.alert.alert_content
    }
    currentAlert.value = currentAccident.value.alert
  }
  alertModalVisible.value = true
}

// 保存警示
const handleSaveAlert = async () => {
  isLoading.value = true
  try {
    const res = await updateAlert(currentAccident.value.id, alertForm.value)
    if (res.status === 'success') {
      alertModalVisible.value = false
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('保存成功')
    } else {
      showMessage(res.message || '保存失败', 'error')
    }
  } catch (e) {
    showMessage('保存失败', 'error')
  }
  isLoading.value = false
}

// 发送警示
const handleSendAlert = async () => {
  if (!confirm('确定发送事故警示？')) return
  isLoading.value = true
  try {
    const res = await sendAlert(currentAccident.value.id)
    if (res.status === 'success') {
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('警示已发送')
    } else {
      showMessage(res.message || '发送失败', 'error')
    }
  } catch (e) {
    showMessage('发送失败', 'error')
  }
  isLoading.value = false
}

// ==================== 培训管理 ====================

// 打开培训弹窗
const openTrainingModal = () => {
  trainingForm.value = {
    training_date: '',
    training_location: '',
    training_content: '',
    trainer_name: '',
    attendees_count: 0,
    sign_sheet_attachment: '',
    photo_attachments: []
  }
  trainingFiles.value = []
  trainingModalVisible.value = true
}

// 上传培训附件
const handleTrainingFileUpload = async (event) => {
  const files = Array.from(event.target.files)
  if (files.length === 0) return
  isLoading.value = true
  try {
    const res = await uploadAccidentAttachments(files)
    if (res.status === 'success') {
      trainingFiles.value.push(...res.data)
    }
  } catch (e) {
    showMessage('上传失败', 'error')
  }
  isLoading.value = false
}

// 保存培训记录
const handleSaveTraining = async () => {
  if (!trainingForm.value.training_date || !trainingForm.value.trainer_name) {
    showMessage('请填写培训日期和培训讲师', 'error')
    return
  }
  isLoading.value = true
  try {
    const res = await addTraining(currentAccident.value.id, {
      ...trainingForm.value,
      photo_attachments: trainingFiles.value
    })
    if (res.status === 'success') {
      trainingModalVisible.value = false
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('培训记录已保存')
    } else {
      showMessage(res.message || '保存失败', 'error')
    }
  } catch (e) {
    showMessage('保存失败', 'error')
  }
  isLoading.value = false
}

// 删除培训记录
const handleDeleteTraining = async (trainingId) => {
  if (!confirm('确定删除这条培训记录？')) return
  isLoading.value = true
  try {
    const res = await deleteTraining(currentAccident.value.id, trainingId)
    if (res.status === 'success') {
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('培训记录已删除')
    } else {
      showMessage(res.message || '删除失败', 'error')
    }
  } catch (e) {
    showMessage('删除失败', 'error')
  }
  isLoading.value = false
}

// ==================== 台账导出与编辑 ====================

// 生成台账
const handleGenerateLedger = async () => {
  if (!currentAccident.value.analysis) {
    showMessage('请先进行AI分析', 'error')
    return
  }
  isLoading.value = true
  try {
    const res = await generateLedger(currentAccident.value.id)
    if (res.status === 'success') {
      showMessage('台账已生成')
      window.open(res.data.ledger_path, '_blank')
      // 刷新详情
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
    } else {
      showMessage(res.message || '生成失败', 'error')
    }
  } catch (e) {
    showMessage('生成失败', 'error')
  }
  isLoading.value = false
}

// 打开台账编辑弹窗
const openLedgerEditModal = async () => {
  isLoading.value = true
  try {
    const res = await fetchLedgerContent(currentAccident.value.id)
    if (res.status === 'success') {
      ledgerContent.value = res.data
      ledgerEditModalVisible.value = true
    } else {
      showMessage(res.message || '获取台账内容失败', 'error')
    }
  } catch (e) {
    showMessage('获取台账内容失败', 'error')
  }
  isLoading.value = false
}

// 保存台账编辑
const handleSaveLedgerContent = async () => {
  isLoading.value = true
  try {
    const res = await updateLedgerContent(currentAccident.value.id, ledgerContent.value)
    if (res.status === 'success') {
      ledgerEditModalVisible.value = false
      // 刷新详情
      const detailRes = await fetchAccidentDetail(currentAccident.value.id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
      showMessage('台账内容已保存，可重新生成Word文档')
    } else {
      showMessage(res.message || '保存失败', 'error')
    }
  } catch (e) {
    showMessage('保存失败', 'error')
  }
  isLoading.value = false
}

// 状态显示
const getStatusLabel = (status) => {
  const labels = {
    draft: '草稿',
    submitted: '已提交',
    pending: '待整改',
    in_progress: '整改中',
    completed: '已完成',
    overdue: '已逾期'
  }
  return labels[status] || status
}

const getStatusClass = (status) => {
  const classes = {
    draft: 'bg-gray-100 text-gray-600',
    submitted: 'bg-green-100 text-green-700',
    pending: 'bg-yellow-100 text-yellow-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    overdue: 'bg-red-100 text-red-700'
  }
  return classes[status] || 'bg-gray-100 text-gray-600'
}

// 初始化加载
onMounted(() => {
  loadAccidents()
})

// 暴露给父组件的方法
defineExpose({
  loadAccidents
})
</script>

<template>
  <div class="max-w-6xl mx-auto p-6">
    <!-- 消息提示 -->
    <div v-if="message" :class="messageType === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'" class="p-3 rounded mb-4 text-center fixed top-4 left-1/2 transform -translate-x-1/2 z-50 shadow-lg">
      {{ message }}
    </div>

    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-blue-800">事故台账</h2>
        <div class="flex space-x-2">
          <button @click="createNew"
                  class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors">
            + 新增事故
          </button>
        </div>
      </div>

      <!-- 逾期提醒 -->
      <div v-if="overdueMeasures.length > 0" class="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex justify-between items-center mb-2">
          <h3 class="text-red-700 font-bold">逾期整改提醒</h3>
          <button @click="checkOverdue" class="px-3 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm">刷新逾期状态</button>
        </div>
        <div class="space-y-2">
          <div v-for="m in overdueMeasures" :key="m.id" class="flex items-center text-sm">
            <span class="text-red-600 mr-2">{{ m.accident_type }}</span>
            <span class="text-gray-600">{{ m.measure_content }}</span>
            <span class="text-red-500 ml-2">责任人: {{ m.responsible_person }}</span>
            <button @click="viewDetail(m.accident_id)" class="ml-2 text-blue-500 hover:text-blue-700">查看</button>
          </div>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="isLoading && accidents.length === 0" class="text-center text-gray-500 py-8">
        加载中...
      </div>

      <!-- 空列表 -->
      <div v-else-if="accidents.length === 0" class="text-center text-gray-500 py-8">
        暂无事故记录
      </div>

      <!-- 事故列表 -->
      <div v-else class="bg-white rounded-lg shadow overflow-hidden">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">事故时间</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">事故类型</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">事故地点</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">部门</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">伤亡</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="accident in accidents" :key="accident.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{{ accident.accident_time }}</td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{{ accident.accident_type }}</td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{{ accident.location }}</td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{{ accident.department || '-' }}</td>
              <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                {{ accident.casualties || '无' }}
              </td>
              <td class="px-4 py-3 whitespace-nowrap">
                <span :class="getStatusClass(accident.status)" class="px-2 py-1 rounded text-xs font-medium">
                  {{ getStatusLabel(accident.status) }}
                </span>
              </td>
              <td class="px-4 py-3 whitespace-nowrap text-sm space-x-2">
                <button @click="viewDetail(accident.id)" class="text-blue-600 hover:text-blue-800 font-medium">详情</button>
                <button v-if="accident.status === 'draft'" @click="editAccident(accident.id)" class="text-green-600 hover:text-green-800 font-medium">编辑</button>
                <button @click="handleDelete(accident.id)" class="text-red-600 hover:text-red-800 font-medium">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 表单视图 -->
    <div v-if="viewMode === 'form'">
      <div class="mb-4">
        <button @click="backToList" class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors">
          ← 返回列表
        </button>
      </div>
      <AccidentForm ref="accidentFormRef" @saved="handleSaved" />
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 overflow-hidden">
        <!-- 弹窗头部 -->
        <div class="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
          <h3 class="text-lg font-bold">事故详情</h3>
          <button @click="closeDetailModal" class="text-white hover:text-gray-200 text-xl">×</button>
        </div>

        <!-- 弹窗内容 -->
        <div class="p-6 max-h-[75vh] overflow-y-auto">
          <!-- 基本信息 -->
          <div class="mb-6">
            <h4 class="text-lg font-bold text-gray-800 mb-3 border-b pb-2">基本信息</h4>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div><span class="text-gray-500">事故时间：</span><span class="text-gray-900">{{ currentAccident?.accident_time }}</span></div>
              <div><span class="text-gray-500">事故类型：</span><span class="text-gray-900">{{ currentAccident?.accident_type }}</span></div>
              <div><span class="text-gray-500">事故地点：</span><span class="text-gray-900">{{ currentAccident?.location }}</span></div>
              <div><span class="text-gray-500">伤亡情况：</span><span class="text-gray-900">{{ currentAccident?.casualties || '无伤亡' }}</span></div>
              <div><span class="text-gray-500">所属部门：</span><span class="text-gray-900">{{ currentAccident?.department || '未填写' }}</span></div>
              <div><span class="text-gray-500">属地工程师：</span><span class="text-gray-900">{{ currentAccident?.engineer_name || '未填写' }}</span></div>
              <div><span class="text-gray-500">状态：</span><span :class="getStatusClass(currentAccident?.status)" class="px-2 py-1 rounded text-xs font-medium">{{ getStatusLabel(currentAccident?.status) }}</span></div>
              <div><span class="text-gray-500">提交时间：</span><span class="text-gray-900">{{ currentAccident?.submitted_at || '未提交' }}</span></div>
            </div>
            <div class="mt-3">
              <span class="text-gray-500">详细描述：</span>
              <p class="mt-1 text-gray-900 bg-gray-50 p-3 rounded">{{ currentAccident?.description || '无描述' }}</p>
            </div>
            <div v-if="currentAccident?.attachments?.length > 0" class="mt-3">
              <span class="text-gray-500">附件：</span>
              <div class="mt-1 space-y-1">
                <a v-for="(path, index) in currentAccident?.attachments" :key="index" :href="path" target="_blank" class="block text-blue-600 hover:text-blue-800 text-sm">{{ decodeURIComponent(path.split('/').pop().split('_').slice(1).join('_')) }}</a>
              </div>
            </div>
          </div>

          <!-- AI分析结果 -->
          <div v-if="currentAccident?.analysis" class="mb-6">
            <h4 class="text-lg font-bold text-gray-800 mb-3 border-b pb-2">AI分析结果</h4>
            <div class="space-y-3">
              <div class="bg-blue-50 p-3 rounded"><h5 class="font-bold text-blue-800 mb-1">直接原因</h5><p class="text-gray-700 text-sm">{{ currentAccident?.analysis?.direct_cause }}</p></div>
              <div class="bg-yellow-50 p-3 rounded"><h5 class="font-bold text-yellow-800 mb-1">间接原因</h5><p class="text-gray-700 text-sm">{{ currentAccident?.analysis?.indirect_cause }}</p></div>
              <div class="bg-purple-50 p-3 rounded"><h5 class="font-bold text-purple-800 mb-1">事故教训</h5><p class="text-gray-700 text-sm">{{ currentAccident?.analysis?.lessons_learned }}</p></div>
              <div class="bg-green-50 p-3 rounded"><h5 class="font-bold text-green-800 mb-1">整改措施</h5><p class="text-gray-700 text-sm">{{ currentAccident?.analysis?.rectification_measures }}</p></div>
            </div>
          </div>

          <!-- 未分析提示 -->
          <div v-else class="mb-6 text-center text-gray-500 py-4 bg-gray-50 rounded">
            该事故尚未进行AI分析
            <button v-if="currentAccident?.status === 'draft'" @click="reanalyze(currentAccident?.id)" class="mt-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm">提交分析</button>
          </div>

          <!-- 整改措施管理 -->
          <div v-if="currentAccident?.analysis" class="mb-6">
            <div class="flex justify-between items-center mb-3">
              <h4 class="text-lg font-bold text-gray-800 border-b pb-2">整改措施管理</h4>
              <button @click="handleAddMeasure" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm">+ 添加措施</button>
            </div>
            <div v-if="currentAccident?.measures?.length > 0" class="space-y-2">
              <div v-for="(m, idx) in currentAccident?.measures" :key="m.id" class="border rounded p-3">
                <div class="flex justify-between items-start">
                  <div class="flex-1">
                    <span class="text-gray-500 mr-2">{{ idx + 1 }}.</span>
                    <span class="text-gray-900">{{ m.measure_content }}</span>
                  </div>
                  <span :class="getStatusClass(m.status)" class="px-2 py-1 rounded text-xs">{{ getStatusLabel(m.status) }}</span>
                </div>
                <div class="mt-2 text-sm text-gray-500 flex justify-between">
                  <span>责任人: {{ m.responsible_person || '未指派' }}</span>
                  <span>期限: {{ m.deadline || '未设置' }}</span>
                </div>
                <div class="mt-2 flex space-x-2">
                  <button v-if="m.status === 'pending'" @click="openAssignModal(m)" class="px-2 py-1 bg-yellow-500 hover:bg-yellow-600 text-white rounded text-xs">指派责任人</button>
                  <button v-if="m.status === 'in_progress'" @click="openCompleteModal(m)" class="px-2 py-1 bg-green-500 hover:bg-green-600 text-white rounded text-xs">标记完成</button>
                  <button v-if="m.status === 'completed'" class="px-2 py-1 bg-gray-300 text-gray-600 rounded text-xs">已完成</button>
                </div>
              </div>
            </div>
            <div v-else class="text-gray-500 text-center py-3">暂无整改措施，请添加</div>
          </div>

          <!-- 事故警示 -->
          <div v-if="currentAccident?.analysis" class="mb-6">
            <div class="flex justify-between items-center mb-3">
              <h4 class="text-lg font-bold text-gray-800 border-b pb-2">事故警示</h4>
              <div class="space-x-2">
                <button v-if="!currentAccident?.alert" @click="handleGenerateAlert" class="px-3 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded text-sm">生成警示</button>
                <button v-if="currentAccident?.alert" @click="openAlertModal" class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm">编辑警示</button>
                <button v-if="currentAccident?.alert && currentAccident?.alert?.status === 'draft'" @click="handleSendAlert" class="px-3 py-1 bg-green-500 hover:bg-green-600 text-white rounded text-sm">发送警示</button>
              </div>
            </div>
            <div v-if="currentAccident?.alert" class="border rounded p-3">
              <h5 class="font-bold text-red-700 mb-2">{{ currentAccident?.alert?.alert_title }}</h5>
              <p class="text-gray-700 text-sm">{{ currentAccident?.alert?.alert_content }}</p>
              <div class="mt-2 text-sm">
                <span class="text-gray-500">状态：</span>
                <span :class="getStatusClass(currentAccident?.alert?.status)" class="px-2 py-1 rounded text-xs">{{ getStatusLabel(currentAccident?.alert?.status) }}</span>
              </div>
            </div>
            <div v-else class="text-gray-500 text-center py-3">暂未生成事故警示</div>
          </div>

          <!-- 培训记录 -->
          <div v-if="currentAccident?.alert" class="mb-6">
            <div class="flex justify-between items-center mb-3">
              <h4 class="text-lg font-bold text-gray-800 border-b pb-2">培训记录</h4>
              <button @click="openTrainingModal" class="px-3 py-1 bg-purple-500 hover:bg-purple-600 text-white rounded text-sm">+ 添加培训</button>
            </div>
            <div v-if="currentAccident?.trainings?.length > 0" class="space-y-2">
              <div v-for="t in currentAccident?.trainings" :key="t.id" class="border rounded p-3">
                <div class="flex justify-between items-center">
                  <div>
                    <span class="font-medium">{{ t.training_date }}</span>
                    <span class="text-gray-500 ml-2">讲师: {{ t.trainer_name }}</span>
                  </div>
                  <button @click="handleDeleteTraining(t.id)" class="text-red-500 hover:text-red-700 text-sm">删除</button>
                </div>
                <div class="mt-1 text-sm text-gray-600">
                  <span>地点: {{ t.training_location }}</span>
                  <span class="ml-4">人数: {{ t.attendees_count }}人</span>
                </div>
                <div v-if="t.photo_attachments?.length > 0" class="mt-1 text-sm text-blue-500">
                  已上传 {{ t.photo_attachments.length }} 个附件
                </div>
              </div>
            </div>
            <div v-else class="text-gray-500 text-center py-3">暂无培训记录</div>
          </div>

          <!-- 台账导出 -->
          <div v-if="currentAccident?.analysis" class="mb-4">
            <h4 class="text-lg font-bold text-gray-800 mb-3 border-b pb-2">台账导出</h4>
            <div class="flex space-x-3">
              <button @click="openLedgerEditModal" class="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded text-sm">编辑台账内容</button>
              <button @click="handleGenerateLedger" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm">生成Word台账</button>
            </div>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="bg-gray-100 px-6 py-4 flex justify-end space-x-2">
          <button v-if="currentAccident?.status === 'submitted'" @click="reanalyze(currentAccident?.id)" :disabled="isLoading" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded font-medium">{{ isLoading ? '分析中...' : '重新分析' }}</button>
          <button @click="closeDetailModal" class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded font-medium">关闭</button>
        </div>
      </div>
    </div>

    <!-- 指派责任人弹窗 -->
    <div v-if="assignModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-bold mb-4">指派整改责任人</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-gray-700 mb-1">责任人姓名</label>
            <input v-model="assignForm.responsible_person" type="text" class="w-full border rounded p-2" placeholder="请输入责任人姓名">
          </div>
          <div>
            <label class="block text-gray-700 mb-1">整改期限</label>
            <input v-model="assignForm.deadline" type="datetime-local" class="w-full border rounded p-2">
          </div>
        </div>
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="assignModalVisible = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
          <button @click="handleAssign" :disabled="isLoading" class="px-4 py-2 bg-blue-500 text-white rounded">{{ isLoading ? '处理中...' : '确认' }}</button>
        </div>
      </div>
    </div>

    <!-- 完成整改弹窗 -->
    <div v-if="completeModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-bold mb-4">标记整改完成</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-gray-700 mb-1">上传完成证明附件</label>
            <input type="file" multiple accept=".jpg,.png,.pdf,.doc,.docx" @change="handleCompleteFileUpload" class="w-full border rounded p-2">
          </div>
          <div v-if="completeFiles.length > 0" class="text-sm text-gray-600">
            已上传: {{ completeFiles.length }} 个文件
          </div>
        </div>
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="completeModalVisible = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
          <button @click="handleComplete" :disabled="isLoading" class="px-4 py-2 bg-green-500 text-white rounded">{{ isLoading ? '处理中...' : '确认完成' }}</button>
        </div>
      </div>
    </div>

    <!-- 警示编辑弹窗 -->
    <div v-if="alertModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
        <h3 class="text-lg font-bold mb-4">编辑事故警示</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-gray-700 mb-1">警示标题</label>
            <input v-model="alertForm.alert_title" type="text" class="w-full border rounded p-2">
          </div>
          <div>
            <label class="block text-gray-700 mb-1">警示内容</label>
            <textarea v-model="alertForm.alert_content" rows="6" class="w-full border rounded p-2"></textarea>
          </div>
        </div>
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="alertModalVisible = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
          <button @click="handleSaveAlert" :disabled="isLoading" class="px-4 py-2 bg-blue-500 text-white rounded">{{ isLoading ? '处理中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 培训记录弹窗 -->
    <div v-if="trainingModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
      <div class="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 p-6">
        <h3 class="text-lg font-bold mb-4">添加培训记录</h3>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-gray-700 mb-1">培训日期</label>
              <input v-model="trainingForm.training_date" type="datetime-local" class="w-full border rounded p-2">
            </div>
            <div>
              <label class="block text-gray-700 mb-1">培训地点</label>
              <input v-model="trainingForm.training_location" type="text" class="w-full border rounded p-2">
            </div>
          </div>
          <div>
            <label class="block text-gray-700 mb-1">培训内容</label>
            <input v-model="trainingForm.training_content" type="text" class="w-full border rounded p-2">
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-gray-700 mb-1">培训讲师</label>
              <input v-model="trainingForm.trainer_name" type="text" class="w-full border rounded p-2">
            </div>
            <div>
              <label class="block text-gray-700 mb-1">参加人数</label>
              <input v-model="trainingForm.attendees_count" type="number" class="w-full border rounded p-2">
            </div>
          </div>
          <div>
            <label class="block text-gray-700 mb-1">上传培训资料（签到表、照片等）</label>
            <input type="file" multiple accept=".jpg,.png,.pdf,.doc,.docx" @change="handleTrainingFileUpload" class="w-full border rounded p-2">
          </div>
        </div>
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="trainingModalVisible = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
          <button @click="handleSaveTraining" :disabled="isLoading" class="px-4 py-2 bg-purple-500 text-white rounded">{{ isLoading ? '处理中...' : '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 台账编辑弹窗 -->
    <div v-if="ledgerEditModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60">
      <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-bold mb-4">编辑台账内容</h3>
        <div class="space-y-4">
          <!-- 基本信息 -->
          <div class="border rounded p-3">
            <h4 class="font-bold text-gray-700 mb-2">基本信息</h4>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-gray-600 mb-1 text-sm">所属部门</label>
                <input v-model="ledgerContent.basic_info.department" type="text" class="w-full border rounded p-2 text-sm">
              </div>
              <div>
                <label class="block text-gray-600 mb-1 text-sm">属地工程师</label>
                <input v-model="ledgerContent.basic_info.engineer_name" type="text" class="w-full border rounded p-2 text-sm">
              </div>
            </div>
            <div class="mt-2">
              <label class="block text-gray-600 mb-1 text-sm">事故描述</label>
              <textarea v-model="ledgerContent.basic_info.description" rows="3" class="w-full border rounded p-2 text-sm"></textarea>
            </div>
          </div>

          <!-- AI分析结果 -->
          <div v-if="ledgerContent.analysis" class="border rounded p-3">
            <h4 class="font-bold text-gray-700 mb-2">AI分析结果</h4>
            <div class="space-y-2">
              <div>
                <label class="block text-gray-600 mb-1 text-sm">直接原因</label>
                <textarea v-model="ledgerContent.analysis.direct_cause" rows="2" class="w-full border rounded p-2 text-sm"></textarea>
              </div>
              <div>
                <label class="block text-gray-600 mb-1 text-sm">间接原因</label>
                <textarea v-model="ledgerContent.analysis.indirect_cause" rows="2" class="w-full border rounded p-2 text-sm"></textarea>
              </div>
              <div>
                <label class="block text-gray-600 mb-1 text-sm">事故教训</label>
                <textarea v-model="ledgerContent.analysis.lessons_learned" rows="2" class="w-full border rounded p-2 text-sm"></textarea>
              </div>
              <div>
                <label class="block text-gray-600 mb-1 text-sm">整改措施</label>
                <textarea v-model="ledgerContent.analysis.rectification_measures" rows="3" class="w-full border rounded p-2 text-sm"></textarea>
              </div>
            </div>
          </div>

          <!-- 整改措施执行 -->
          <div v-if="ledgerContent.measures?.length > 0" class="border rounded p-3">
            <h4 class="font-bold text-gray-700 mb-2">整改措施执行情况</h4>
            <div class="space-y-2">
              <div v-for="(m, idx) in ledgerContent.measures" :key="m.id" class="flex items-center space-x-2">
                <span class="text-gray-500">{{ idx + 1 }}.</span>
                <input v-model="m.content" type="text" class="flex-1 border rounded p-2 text-sm">
                <input v-model="m.responsible_person" type="text" placeholder="责任人" class="w-20 border rounded p-2 text-sm">
              </div>
            </div>
          </div>
        </div>
        <div class="mt-4 flex justify-end space-x-2">
          <button @click="ledgerEditModalVisible = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
          <button @click="handleSaveLedgerContent" :disabled="isLoading" class="px-4 py-2 bg-blue-500 text-white rounded">{{ isLoading ? '处理中...' : '保存修改' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>