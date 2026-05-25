<template>
  <div id="app" class="min-h-screen bg-bg-primary">
    <!-- 导航栏 -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-8">
            <h1 class="text-xl font-bold text-purple-600">小红书内容生成</h1>
            <div class="flex gap-4">
              <router-link
                to="/"
                class="px-4 py-2 rounded-lg transition"
                :class="$route.path === '/' ? 'bg-purple-100 text-purple-700 font-semibold' : 'text-gray-600 hover:text-gray-800'"
              >
                🚀 创作工作流
              </router-link>
              <router-link
                to="/pending-tasks"
                class="px-4 py-2 rounded-lg transition"
                :class="$route.path === '/pending-tasks' ? 'bg-purple-100 text-purple-700 font-semibold' : 'text-gray-600 hover:text-gray-800'"
              >
                ⏸️ 待处理任务
              </router-link>
              <router-link
                to="/notes"
                class="px-4 py-2 rounded-lg transition"
                :class="$route.path.startsWith('/notes') ? 'bg-purple-100 text-purple-700 font-semibold' : 'text-gray-600 hover:text-gray-800'"
              >
                📝 我的笔记
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>
