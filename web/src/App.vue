<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatStore } from '@/stores/chat'
import SideBar from './components/layout/SideBar.vue'
import TopBar from './components/layout/TopBar.vue'
import ChatThread from './components/chat/ChatThread.vue'
import ChatInput from './components/input/ChatInput.vue'

const store = useChatStore()
const { currentSession, isGenerating } = storeToRefs(store)

const sidebarOpen = ref(false)

const handleSend = (text: string) => {
  store.sendMessage(text)
  // 发送后如果是移动端，自动收起侧边栏
  sidebarOpen.value = false
}

onMounted(() => {
  // 页面加载自动连接 WebSocket 后端
  store.initWebSocket()
})
</script>

<template>
  <div class="h-screen w-screen flex bg-background text-on-surface overflow-hidden antialiased">
    <!-- 侧边栏 (桌面端融入 Flex，移动端基于 Z-Index 滑出) -->
    <div
      :class="[
        'fixed md:static inset-y-0 left-0 z-40 transform transition-transform duration-300 md:translate-x-0 flex-shrink-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <SideBar />
    </div>

    <!-- 移动端滑出抽屉遮罩 -->
    <div
      v-if="sidebarOpen"
      @click="sidebarOpen = false"
      class="fixed inset-0 bg-black/60 z-30 md:hidden transition-opacity duration-300"
    ></div>

    <!-- 右侧核心诊断视窗 -->
    <div class="flex-1 flex flex-col h-full min-w-0 relative">
      <!-- 头部状态栏 -->
      <TopBar
        :sidebar-open="sidebarOpen"
        @toggle-sidebar="sidebarOpen = !sidebarOpen"
      />
      
      <!-- 聊天内容区域 -->
      <ChatThread :messages="currentSession?.messages || []" />
      
      <!-- 底部输入栏 -->
      <ChatInput
        :disabled="isGenerating"
        @send="handleSend"
      />
    </div>
  </div>
</template>

<style>
/* 注入一些全局修饰样式 */
html, body, #app {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
}
</style>
