<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  toolName: string
  input?: any
  output?: string
  isError?: boolean
  loading?: boolean
}>()

const isOpen = ref(false)

const toggleOpen = () => {
  if (props.loading) return // 加载中不可点击展开
  isOpen.value = !isOpen.value
}
</script>

<template>
  <div class="self-start flex flex-col gap-xs mt-xs max-w-full">
    <!-- Pill Trigger -->
    <div
      @click="toggleOpen"
      :class="[
        'inline-flex items-center gap-xs px-sm py-xs rounded-full border text-code-sm font-code-sm select-none',
        loading ? 'cursor-wait' : 'cursor-pointer hover:bg-opacity-50 transition-all',
        isError
          ? 'bg-error-container/20 border-error text-error'
          : 'bg-[#354a43] border-primary/30 text-primary'
      ]"
    >
      <span class="material-symbols-outlined text-[14px]">terminal</span>
      <span>[tool] {{ toolName }}</span>
      <span class="text-on-surface-variant/60 mx-xs">•</span>
      <span class="truncate max-w-[200px] opacity-80" :title="input ? JSON.stringify(input) : ''">
        {{ input ? JSON.stringify(input) : '...' }}
      </span>
      
      <!-- Status Icon -->
      <span v-if="loading" class="animate-spin text-[12px] inline-block font-bold">⟳</span>
      <span v-else-if="isError" class="text-[12px] text-error font-bold" style="font-family: Arial;">✗</span>
      <span v-else class="text-[12px] text-primary" style="font-family: Arial;">✓</span>
    </div>

    <!-- Collapsible Payload View -->
    <div
      v-if="isOpen && !loading"
      class="mt-xs p-sm border border-outline-variant bg-surface-container-lowest rounded-sm font-code-sm text-code-sm text-on-surface-variant max-w-full overflow-x-auto terminal-scroll"
    >
      <div v-if="input" class="mb-xs">
        <span class="text-primary opacity-60 font-semibold">&gt; Input:</span>
        <pre class="pl-sm text-on-surface whitespace-pre-wrap">{{ JSON.stringify(input, null, 2) }}</pre>
      </div>
      <div v-if="output">
        <span class="text-secondary opacity-60 font-semibold">&gt; Output:</span>
        <pre class="pl-sm text-on-surface-variant whitespace-pre-wrap">{{ output }}</pre>
      </div>
    </div>
  </div>
</template>
