<script setup>
import { ref, onMounted } from 'vue'
import { fetchPrompts, savePrompt, aiImprovePrompt, fetchDictionary, saveDictionary } from '../api/admin.js'

// 提示词管理状态
const systemPrompts = ref([])
const aiOptimizerVisible = ref({})
const auditIssuesFeedback = ref({})
const isOptimizing = ref(false)

// 字典配置状态
const dictionaryJson = ref('')

// 加载提示词列表（只加载审核相关）
const loadPrompts = async () => {
  const data = await fetchPrompts()
  if (data.status === 'success') {
    // 只加载审核相关的提示词，排除事故相关的
    systemPrompts.value = (data.data || [])
      .filter(p => !p.prompt_key.includes('accident'))
      .map(p => ({
        ...p,
        isExpanded: false,
        isEditing: false,
        tempContent: p.content
      }))
  }
}

// 保存单个提示词
const handleSavePrompt = async (prompt) => {
  await savePrompt(prompt.prompt_key, prompt.tempContent)
  prompt.content = prompt.tempContent
  prompt.isEditing = false
  alert('提示词保存成功！')
}

// AI 优化提示词
const handleAiImprove = async (prompt) => {
  const feedback = auditIssuesFeedback.value[prompt.prompt_key]
  if (!feedback) return alert('请输入你在审核中遇到的问题或改进期望')

  isOptimizing.value = true
  try {
    const data = await aiImprovePrompt(prompt.tempContent, feedback)
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

// 加载字典配置
const loadDictionary = async () => {
  const data = await fetchDictionary()
  if (data.status === 'success') {
    dictionaryJson.value = JSON.stringify(data.data, null, 2)
  }
}

// 保存字典配置
const handleSaveDictionary = async () => {
  try {
    const parsed = JSON.parse(dictionaryJson.value)
    await saveDictionary(parsed)
    alert('匹配字典已更新生效！')
  } catch (e) {
    alert('JSON 格式有误，请检查标点符号是否配对！')
  }
}

// 暴露给父组件的方法
defineExpose({
  loadPrompts,
  loadDictionary
})

onMounted(() => {
  loadPrompts()
  loadDictionary()
})
</script>

<template>
  <div class="space-y-8">
    <!-- Prompt 管理 -->
    <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-blue-500">
      <h2 class="text-2xl font-bold text-gray-800 mb-6">🧠 核心审核大模型 Prompt 管理</h2>
      <p class="text-sm text-gray-500 mb-4">通过调优提示词，可以直接改变 AI 判罚的尺度和侧重点。所有变量（如 {standard_text}）请务必保留。</p>

      <div class="space-y-4">
        <div v-for="prompt in systemPrompts" :key="prompt.prompt_key" class="border rounded-lg overflow-hidden">
          <div
            @click="prompt.isExpanded = !prompt.isExpanded"
            class="bg-gray-50 p-4 cursor-pointer hover:bg-gray-100 flex justify-between items-center transition-colors"
          >
            <div>
              <span class="font-bold text-lg text-blue-900">{{ prompt.prompt_name }}</span>
              <span class="ml-4 text-xs text-gray-400">最后更新: {{ prompt.updated_at }}</span>
            </div>
            <svg class="w-6 h-6 transform transition-transform" :class="prompt.isExpanded ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
            </svg>
          </div>

          <div v-show="prompt.isExpanded" class="p-4 bg-white border-t">
            <div v-if="!prompt.isEditing" class="bg-gray-900 text-green-400 p-4 rounded-md font-mono text-sm whitespace-pre-wrap leading-relaxed">
              {{ prompt.content }}
            </div>
            <textarea
              v-else
              v-model="prompt.tempContent"
              class="w-full h-64 p-4 border-2 border-blue-300 rounded-md font-mono text-sm focus:ring focus:ring-blue-200 outline-none"
            ></textarea>

            <div class="mt-4 flex justify-between items-center">
              <div class="space-x-3">
                <button
                  v-if="!prompt.isEditing"
                  @click="prompt.isEditing = true"
                  class="px-4 py-2 bg-blue-100 text-blue-700 font-bold rounded hover:bg-blue-200"
                >
                  编辑提示词
                </button>
                <template v-else>
                  <button @click="handleSavePrompt(prompt)" class="px-4 py-2 bg-green-600 text-white font-bold rounded hover:bg-green-700 shadow-sm">
                    💾 保存生效
                  </button>
                  <button @click="prompt.isEditing = false; prompt.tempContent = prompt.content" class="px-4 py-2 bg-gray-200 text-gray-700 font-bold rounded hover:bg-gray-300">
                    取消
                  </button>
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
                @click="handleAiImprove(prompt)"
                :disabled="isOptimizing"
                class="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold rounded shadow hover:shadow-lg disabled:opacity-50 flex items-center"
              >
                <svg v-if="isOptimizing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ isOptimizing ? '大模型深度思考重写中...' : '开始重写提示词' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 字典配置管理 -->
    <div class="bg-white p-6 rounded-lg shadow-md border-t-4 border-green-500">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">📂 体系条款与文件匹配字典</h2>
          <p class="text-sm text-gray-500 mt-1">全局路由配置 `element_routing_dictionary_final.json`，修改后立即生效。</p>
        </div>
        <button @click="handleSaveDictionary" class="px-6 py-2 bg-green-600 text-white font-bold rounded shadow hover:bg-green-700">
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
</template>