<script setup>
import { ref } from 'vue'

const emit = defineEmits(['select'])

const selectSystem = (system) => {
  emit('select', system)
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-8">
    <!-- 平台标题 -->
    <div class="text-center mb-12">
      <h1 class="text-5xl font-bold text-gray-800 mb-4">EHS 智能体平台</h1>
      <p class="text-xl text-gray-600">选择您要进入的系统</p>
    </div>

    <!-- 系统卡片 -->
    <div class="flex gap-8 max-w-4xl">
      <!-- ISO审核系统卡片 -->
      <div
        @click="selectSystem('audit')"
        class="w-80 bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-blue-500 group"
      >
        <div class="p-8">
          <div class="w-16 h-16 bg-blue-100 rounded-xl flex items-center justify-center mb-6 group-hover:bg-blue-200 transition-colors">
            <span class="text-3xl">📋</span>
          </div>
          <h2 class="text-2xl font-bold text-gray-800 mb-3">ISO 体系智能审核系统</h2>
          <p class="text-gray-600 mb-6">对ISO体系文件进行智能审核，生成综合审核报告，管理审核历史记录。</p>
          <div class="space-y-2 text-sm text-gray-500">
            <div class="flex items-center">
              <span class="text-green-500 mr-2">✓</span>
              <span>审核工作台</span>
            </div>
            <div class="flex items-center">
              <span class="text-green-500 mr-2">✓</span>
              <span>报告中心</span>
            </div>
            <div class="flex items-center">
              <span class="text-green-500 mr-2">✓</span>
              <span>引擎配置中台</span>
            </div>
          </div>
        </div>
        <div class="px-8 pb-8">
          <button class="w-full py-3 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition-colors">
            进入系统
          </button>
        </div>
      </div>

      <!-- 事故分析系统卡片 -->
      <div
        @click="selectSystem('accident')"
        class="w-80 bg-white rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer border-2 border-transparent hover:border-orange-500 group"
      >
        <div class="p-8">
          <div class="w-16 h-16 bg-orange-100 rounded-xl flex items-center justify-center mb-6 group-hover:bg-orange-200 transition-colors">
            <span class="text-3xl">⚠️</span>
          </div>
          <h2 class="text-2xl font-bold text-gray-800 mb-3">事故分析系统</h2>
          <p class="text-gray-600 mb-6">录入事故信息，AI智能分析原因，管理整改措施闭环，生成事故台账。</p>
          <div class="space-y-2 text-sm text-gray-500">
            <div class="flex items-center">
              <span class="text-green-500 mr-2">✓</span>
              <span>事故录入</span>
            </div>
            <div class="flex items-center">
              <span class="text-green-500 mr-2">✓</span>
              <span>事故台账</span>
            </div>
          </div>
        </div>
        <div class="px-8 pb-8">
          <button class="w-full py-3 bg-orange-600 text-white rounded-lg font-bold hover:bg-orange-700 transition-colors">
            进入系统
          </button>
        </div>
      </div>
    </div>

    <!-- 版权信息 -->
    <div class="mt-12 text-center text-gray-500 text-sm">
      <p>© 2026 EHS智能体平台 | 安全 · 健康 · 环境</p>
    </div>
  </div>
</template>

<style scoped>
</style>