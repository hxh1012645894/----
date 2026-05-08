<script setup>
import { ref } from 'vue'
import { createAccident, updateAccident, uploadAccidentAttachments, submitAccidentForAnalysis } from '../api/accident.js'

// 事故类型选项（固定列表）
const accidentTypes = [
  '火灾事故',
  '爆炸事故',
  '中毒事故',
  '泄漏事故',
  '机械伤害',
  '高处坠落',
  '物体打击',
  '触电事故',
  '灼烫事故',
  '其他事故'
]

// 表单数据
const accidentTime = ref('')
const location = ref('')
const accidentType = ref(accidentTypes[0])
const casualties = ref('')
const description = ref('')
const attachments = ref([])
const uploadedFiles = ref([])
const department = ref('')
const engineerName = ref('')

// 状态
const isLoading = ref(false)
const isAnalyzing = ref(false)
const editingId = ref(null)
const message = ref('')
const messageType = ref('success')

// emit
const emit = defineEmits(['saved'])

// 文件上传处理
const handleFileUpload = async (event) => {
  const files = Array.from(event.target.files)
  if (files.length === 0) return

  isLoading.value = true
  try {
    const res = await uploadAccidentAttachments(files)
    if (res.status === 'success') {
      res.data.forEach(path => {
        const fileName = decodeURIComponent(path.split('/').pop().split('_').slice(1).join('_'))
        uploadedFiles.value.push({ path, name: fileName })
        attachments.value.push(path)
      })
    }
  } catch (e) {
    showMessage('附件上传失败', 'error')
  }
  isLoading.value = false
  event.target.value = ''
}

// 移除附件
const removeAttachment = (index) => {
  uploadedFiles.value.splice(index, 1)
  attachments.value.splice(index, 1)
}

// 显示消息
const showMessage = (text, type = 'success') => {
  message.value = text
  messageType.value = type
  setTimeout(() => { message.value = '' }, 3000)
}

// 保存草稿
const saveDraft = async () => {
  if (!accidentTime.value || !location.value || !accidentType.value) {
    showMessage('请填写必填字段', 'error')
    return
  }

  isLoading.value = true
  try {
    const data = {
      accident_time: accidentTime.value,
      location: location.value,
      accident_type: accidentType.value,
      casualties: casualties.value,
      description: description.value,
      attachments: attachments.value,
      department: department.value,
      engineer_name: engineerName.value,
      status: 'draft'
    }

    let res
    if (editingId.value) {
      res = await updateAccident(editingId.value, data)
    } else {
      res = await createAccident(data)
      if (res.status === 'success') {
        editingId.value = res.data.id
      }
    }

    if (res.status === 'success') {
      showMessage('保存成功')
      emit('saved')
    } else {
      showMessage(res.message || '保存失败', 'error')
    }
  } catch (e) {
    showMessage('保存失败', 'error')
  }
  isLoading.value = false
}

// 提交分析
const submitAnalysis = async () => {
  if (!accidentTime.value || !location.value || !accidentType.value) {
    showMessage('请填写必填字段', 'error')
    return
  }

  isAnalyzing.value = true
  try {
    const data = {
      accident_time: accidentTime.value,
      location: location.value,
      accident_type: accidentType.value,
      casualties: casualties.value,
      description: description.value,
      attachments: attachments.value,
      department: department.value,
      engineer_name: engineerName.value,
      status: 'draft'
    }

    let res
    if (editingId.value) {
      await updateAccident(editingId.value, data)
      res = await submitAccidentForAnalysis(editingId.value)
    } else {
      const createRes = await createAccident(data)
      if (createRes.status === 'success') {
        editingId.value = createRes.data.id
        res = await submitAccidentForAnalysis(editingId.value)
      } else {
        showMessage(createRes.message || '创建失败', 'error')
        isAnalyzing.value = false
        return
      }
    }

    if (res.status === 'success') {
      showMessage('AI分析完成')
      emit('saved')
      resetForm()
    } else {
      showMessage(res.message || '分析失败', 'error')
    }
  } catch (e) {
    showMessage('提交失败', 'error')
  }
  isAnalyzing.value = false
}

// 重置表单
const resetForm = () => {
  accidentTime.value = ''
  location.value = ''
  accidentType.value = accidentTypes[0]
  casualties.value = ''
  description.value = ''
  attachments.value = []
  uploadedFiles.value = []
  department.value = ''
  engineerName.value = ''
  editingId.value = null
}

// 暴露给父组件的方法
defineExpose({
  resetForm,
  loadAccident: (accident) => {
    editingId.value = accident.id
    accidentTime.value = accident.accident_time
    location.value = accident.location
    accidentType.value = accident.accident_type
    casualties.value = accident.casualties
    description.value = accident.description || ''
    attachments.value = accident.attachments || []
    uploadedFiles.value = (accident.attachments || []).map(path => {
      const fileName = decodeURIComponent(path.split('/').pop().split('_').slice(1).join('_'))
      return { path, name: fileName }
    })
    department.value = accident.department || ''
    engineerName.value = accident.engineer_name || ''
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-md">
    <h2 class="text-2xl font-bold text-blue-800 mb-6">事故信息录入</h2>

    <!-- 消息提示 -->
    <div v-if="message" :class="messageType === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'" class="p-3 rounded mb-4 text-center">
      {{ message }}
    </div>

    <!-- 表单 -->
    <div class="space-y-4">
      <!-- 事故时间 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">事故发生时间 *</label>
        <input type="datetime-local" v-model="accidentTime" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
      </div>

      <!-- 事故地点 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">事故地点 *</label>
        <input type="text" v-model="location" placeholder="请输入事故发生地点" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
      </div>

      <!-- 事故类型 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">事故类型 *</label>
        <select v-model="accidentType" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
          <option v-for="type in accidentTypes" :key="type" :value="type">{{ type }}</option>
        </select>
      </div>

      <!-- 所属部门 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">所属部门</label>
        <input type="text" v-model="department" placeholder="请输入事故发生部门" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
      </div>

      <!-- 属地工程师 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">属地工程师</label>
        <input type="text" v-model="engineerName" placeholder="请输入属地工程师姓名" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
      </div>

      <!-- 伤亡情况 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">伤亡情况</label>
        <input type="text" v-model="casualties" placeholder="请输入伤亡情况（如：轻伤2人，重伤1人）" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
      </div>

      <!-- 详细描述 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">事故详细描述</label>
        <textarea v-model="description" rows="4" placeholder="请详细描述事故经过、原因等信息" class="block w-full rounded-md border-gray-300 border p-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"></textarea>
      </div>

      <!-- 附件上传 -->
      <div>
        <label class="block text-gray-700 font-medium mb-1">附件上传（事故调查报告等）</label>
        <input type="file" multiple accept=".doc,.docx,.pdf,.xlsx,.jpg,.png" @change="handleFileUpload" class="block w-full border p-2 rounded-md cursor-pointer">
        <!-- 已上传文件列表 -->
        <div v-if="uploadedFiles.length > 0" class="mt-2 space-y-1">
          <div v-for="(file, index) in uploadedFiles" :key="index" class="flex items-center justify-between bg-gray-50 p-2 rounded">
            <span class="text-sm text-gray-600">{{ file.name }}</span>
            <button @click="removeAttachment(index)" class="text-red-500 hover:text-red-700 text-sm">删除</button>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex space-x-4 pt-4">
        <button @click="saveDraft" :disabled="isLoading || isAnalyzing" :class="isLoading ? 'bg-gray-400' : 'bg-blue-500 hover:bg-blue-600'" class="px-6 py-2 rounded-lg text-white font-medium transition-colors">
          {{ isLoading ? '处理中...' : '保存草稿' }}
        </button>
        <button @click="submitAnalysis" :disabled="isLoading || isAnalyzing" :class="isAnalyzing ? 'bg-yellow-500' : 'bg-green-500 hover:bg-green-600'" class="px-6 py-2 rounded-lg text-white font-medium transition-colors">
          {{ isAnalyzing ? 'AI分析中...' : '提交分析' }}
        </button>
        <button @click="resetForm" class="px-6 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium transition-colors">
          重置
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>