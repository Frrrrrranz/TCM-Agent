<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

const text = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const handleInput = () => {
  const el = textareaRef.value
  if (!el) return
  
  // 自动伸缩高度逻辑
  el.style.height = 'auto'
  el.style.height = `${Math.min(200, el.scrollHeight)}px`
}

const submit = () => {
  if (props.disabled || !text.value.trim()) return
  emit('send', text.value.trim())
  text.value = ''
  
  // 重置高度
  const el = textareaRef.value
  if (el) {
    el.style.height = 'auto'
  }
}

const handleKeydown = (e: KeyboardEvent) => {
  // Enter 键直接发送，Shift + Enter 键换行
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <footer class="w-full bg-surface-container-low border-t border-outline-variant p-gutter flex-shrink-0 z-20">
    <div class="max-w-[1024px] mx-auto">
      <div class="relative bg-surface-dim border border-outline-variant rounded-sm focus-within:border-primary transition-colors flex items-end">
        <!-- CLI 前导提示符 -->
        <span class="absolute left-sm bottom-[14px] text-primary font-code-sm font-bold select-none">&gt;</span>
        
        <!-- Terminal-like Textarea -->
        <textarea
          ref="textareaRef"
          v-model="text"
          @input="handleInput"
          @keydown="handleKeydown"
          :disabled="disabled"
          class="w-full bg-transparent border-none text-on-surface font-body-md focus:ring-0 focus:outline-none resize-none pl-xl pr-[60px] py-sm min-h-[46px] max-h-[200px] terminal-scroll placeholder-on-surface-variant/40"
          placeholder="输入病情观察、脉象、舌象或中药提问..."
          rows="1"
        ></textarea>
        
        <!-- 发送按钮 -->
        <button
          @click="submit"
          :disabled="disabled || !text.trim()"
          class="absolute right-sm bottom-sm bg-primary text-on-primary p-xs rounded-sm hover:bg-primary-fixed transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center"
          title="发送"
        >
          <span class="material-symbols-outlined text-[18px]">send</span>
        </button>
      </div>
      
      <!-- 快捷提示说明 -->
      <div class="mt-xs flex justify-between items-center px-xs select-none">
        <span class="font-code-sm text-code-sm text-on-surface-variant opacity-50">
          临床命令：输入 '/' 呼出模板 (例如 /pulse, /tongue)
        </span>
        <span class="font-code-sm text-code-sm text-on-surface-variant opacity-50 hidden sm:block">
          Shift + Enter 换行，Enter 直接发送
        </span>
      </div>
    </div>
  </footer>
</template>
