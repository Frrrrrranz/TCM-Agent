<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'

const store = useChatStore()
const { isConnected, modelName, tokensUsed, tokensLimit } = storeToRefs(store)

defineProps<{
  sidebarOpen: boolean
}>()

defineEmits<{
  (e: 'toggle-sidebar'): void
}>()

// 格式化 Token 数，如 4200 -> 4.2k
const formatTokens = (num: number) => {
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}

const tokenPercentage = computed(() => {
  return Math.min(100, (tokensUsed.value / tokensLimit.value) * 100)
})
</script>

<template>
  <header class="bg-surface-container border-b border-outline-variant w-full h-14 flex items-center justify-between px-gutter flex-shrink-0 z-30">
    <div class="flex items-center gap-sm md:gap-lg">
      <!-- 移动端 Sidebar 开关 -->
      <button
        @click="$emit('toggle-sidebar')"
        class="md:hidden p-xs text-on-surface-variant hover:text-primary transition-colors cursor-pointer flex items-center"
        aria-label="Toggle menu"
      >
        <span class="material-symbols-outlined">{{ sidebarOpen ? 'close' : 'menu' }}</span>
      </button>
      
      <div class="flex items-center gap-sm">
        <span class="font-headline-md text-headline-md text-primary font-bold">{{ modelName }}</span>
        <!-- 连接状态指示器 -->
        <span
          :class="[
            'w-2 h-2 rounded-full inline-block transition-all duration-300',
            isConnected ? 'bg-primary shadow-[0_0_8px_#83d7b5]' : 'bg-error animate-pulse shadow-[0_0_8px_#ffb4ab]'
          ]"
          :title="isConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'"
        ></span>
      </div>
      
      <div class="hidden sm:flex items-center gap-sm">
        <span class="font-code-sm text-code-sm text-on-surface-variant bg-surface-container-high px-sm py-xs rounded-sm border border-outline-variant">
          Tokens: {{ formatTokens(tokensUsed) }} / {{ formatTokens(tokensLimit) }}
        </span>
      </div>
    </div>
    
    <!-- 右侧状态/设置 -->
    <div class="flex items-center gap-md">
      <!-- 移动端 Token 进度条 -->
      <div class="sm:hidden flex flex-col items-end min-w-[70px]">
        <span class="font-code-sm text-code-sm text-on-surface-variant opacity-70">
          Tokens: {{ formatTokens(tokensUsed) }}
        </span>
        <div class="h-[2px] w-16 bg-surface-container-highest mt-1 rounded-full overflow-hidden">
          <div class="h-full bg-primary transition-all duration-300" :style="{ width: `${tokenPercentage}%` }"></div>
        </div>
      </div>
      
      <button class="text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high p-sm rounded-sm transition-colors cursor-pointer flex items-center" title="设置">
        <span class="material-symbols-outlined">settings</span>
      </button>
    </div>
  </header>
</template>
