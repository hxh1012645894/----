<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { fetchAccidents, fetchAccidentDetail, deleteAccident, submitAccidentForAnalysis } from '../api/accident.js'
import AccidentForm from './AccidentForm.vue'

// 列表数据
const accidents = ref([])

// 详情弹窗状态
const detailModalVisible = ref(false)
const currentAccident = ref(null)
const isLoading = ref(false)

// 视图模式：list 或 form
const viewMode = ref('list')

// 表单组件引用
const accidentFormRef = ref(null)

// 加载事故列表
const loadAccidents = async () => {
  isLoading.value = true
  try {
    const res = await fetchAccidents()
    if (res.status === 'success') {
      accidents.value = res.data
    }
  } catch (e) {
    console.error('加载事故列表失败', e)
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
      alert(res.message || '获取详情失败')
    }
  } catch (e) {
    alert('获取详情失败')
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
    if (res.status !== 'success') {
      accidents.value = original
      alert(res.message || '删除失败')
    }
  } catch (e) {
    accidents.value = original
    alert('删除失败')
  }
}

// 重新分析
const reanalyze = async (id) => {
  if (!confirm('确定重新进行AI分析？')) return

  isLoading.value = true
  try {
    const res = await submitAccidentForAnalysis(id)
    if (res.status === 'success') {
      alert('AI分析完成')
      // 刷新详情
      const detailRes = await fetchAccidentDetail(id)
      if (detailRes.status === 'success') {
        currentAccident.value = detailRes.data
      }
    } else {
      alert(res.message || '分析失败')
    }
  } catch (e) {
    alert('分析失败')
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
    alert('加载事故数据失败')
  }
  isLoading.value = false
}

// 返回列表
const backToList = () => {
  viewMode.value = 'list'
  loadAccidents()
}

// 关闭详情弹窗
const closeDetailModal = () => {
  detailModalVisible.value = false
  currentAccident.value = null
}

// 状态显示
const getStatusLabel = (status) => {
  return status === 'submitted' ? '已提交' : '未提交'
}

const getStatusClass = (status) => {
  return status === 'submitted' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
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
    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-blue-800">事故台账</h2>
        <button @click="createNew"
                class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors">
          + 新增事故
        </button>
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
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">事故时间</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">事故类型</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">事故地点</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">伤亡情况</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="accident in accidents" :key="accident.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ accident.accident_time }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ accident.accident_type }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ accident.location }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ accident.casualties > 0 ? accident.casualties + '人' : '无伤亡' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="getStatusClass(accident.status)"
                      class="px-2 py-1 rounded text-xs font-medium">
                  {{ getStatusLabel(accident.status) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                <button @click="viewDetail(accident.id)"
                        class="text-blue-600 hover:text-blue-800 font-medium">详情</button>
                <button v-if="accident.status === 'draft'" @click="editAccident(accident.id)"
                        class="text-green-600 hover:text-green-800 font-medium">编辑</button>
                <button @click="handleDelete(accident.id)"
                        class="text-red-600 hover:text-red-800 font-medium">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 表单视图 -->
    <div v-if="viewMode === 'form'">
      <div class="mb-4">
        <button @click="backToList"
                class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors">
          ← 返回列表
        </button>
      </div>
      <AccidentForm ref="accidentFormRef" @saved="backToList" />
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailModalVisible" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 overflow-hidden">
        <!-- 弹窗头部 -->
        <div class="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
          <h3 class="text-lg font-bold">事故详情</h3>
          <button @click="closeDetailModal" class="text-white hover:text-gray-200 text-xl">×</button>
        </div>

        <!-- 弹窗内容 -->
        <div class="p-6 max-h-[70vh] overflow-y-auto">
          <!-- 基本信息 -->
          <div class="mb-6">
            <h4 class="text-lg font-bold text-gray-800 mb-3 border-b pb-2">基本信息</h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <span class="text-gray-500">事故时间：</span>
                <span class="text-gray-900">{{ currentAccident?.accident_time }}</span>
              </div>
              <div>
                <span class="text-gray-500">事故类型：</span>
                <span class="text-gray-900">{{ currentAccident?.accident_type }}</span>
              </div>
              <div>
                <span class="text-gray-500">事故地点：</span>
                <span class="text-gray-900">{{ currentAccident?.location }}</span>
              </div>
              <div>
                <span class="text-gray-500">伤亡人数：</span>
                <span class="text-gray-900">
                  {{ currentAccident?.casualties > 0 ? currentAccident?.casualties + '人' : '无伤亡' }}
                </span>
              </div>
              <div>
                <span class="text-gray-500">状态：</span>
                <span :class="getStatusClass(currentAccident?.status)" class="px-2 py-1 rounded text-xs font-medium">
                  {{ getStatusLabel(currentAccident?.status) }}
                </span>
              </div>
              <div>
                <span class="text-gray-500">提交时间：</span>
                <span class="text-gray-900">{{ currentAccident?.submitted_at || '未提交' }}</span>
              </div>
            </div>

            <!-- 详细描述 -->
            <div class="mt-4">
              <span class="text-gray-500">详细描述：</span>
              <p class="mt-1 text-gray-900 bg-gray-50 p-3 rounded">{{ currentAccident?.description || '无描述' }}</p>
            </div>

            <!-- 附件列表 -->
            <div v-if="currentAccident?.attachments?.length > 0" class="mt-4">
              <span class="text-gray-500">附件：</span>
              <div class="mt-1 space-y-1">
                <a v-for="(path, index) in currentAccident?.attachments" :key="index"
                   :href="path" target="_blank"
                   class="block text-blue-600 hover:text-blue-800 text-sm">
                  {{ decodeURIComponent(path.split('/').pop().split('_').slice(1).join('_')) }}
                </a>
              </div>
            </div>
          </div>

          <!-- AI分析结果 -->
          <div v-if="currentAccident?.analysis" class="mb-6">
            <h4 class="text-lg font-bold text-gray-800 mb-3 border-b pb-2">AI分析结果</h4>
            <div class="space-y-4">
              <div class="bg-blue-50 p-4 rounded">
                <h5 class="font-bold text-blue-800 mb-2">直接原因分析</h5>
                <p class="text-gray-700">{{ currentAccident?.analysis?.direct_cause }}</p>
              </div>
              <div class="bg-yellow-50 p-4 rounded">
                <h5 class="font-bold text-yellow-800 mb-2">间接原因分析</h5>
                <p class="text-gray-700">{{ currentAccident?.analysis?.indirect_cause }}</p>
              </div>
              <div class="bg-purple-50 p-4 rounded">
                <h5 class="font-bold text-purple-800 mb-2">事故教训总结</h5>
                <p class="text-gray-700">{{ currentAccident?.analysis?.lessons_learned }}</p>
              </div>
              <div class="bg-green-50 p-4 rounded">
                <h5 class="font-bold text-green-800 mb-2">整改措施建议</h5>
                <p class="text-gray-700">{{ currentAccident?.analysis?.rectification_measures }}</p>
              </div>
            </div>
            <div class="mt-2 text-sm text-gray-500">
              分析时间：{{ currentAccident?.analysis?.analysis_time }}
            </div>
          </div>

          <!-- 未分析提示 -->
          <div v-else class="mb-6 text-center text-gray-500 py-4 bg-gray-50 rounded">
            该事故尚未进行AI分析
            <button v-if="currentAccident?.status === 'draft'" @click="reanalyze(currentAccident?.id)"
                    class="mt-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm">
              提交分析
            </button>
          </div>
        </div>

        <!-- 弹窗底部 -->
        <div class="bg-gray-100 px-6 py-4 flex justify-end space-x-2">
          <button v-if="currentAccident?.status === 'submitted'" @click="reanalyze(currentAccident?.id)"
                  :disabled="isLoading"
                  class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded font-medium">
            {{ isLoading ? '分析中...' : '重新分析' }}
          </button>
          <button @click="closeDetailModal"
                  class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded font-medium">
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>