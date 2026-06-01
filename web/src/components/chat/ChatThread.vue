<script setup lang="ts">
import { ref, watch, nextTick, computed, onMounted } from 'vue'
import UserMessage from './UserMessage.vue'
import AgentMessage from './AgentMessage.vue'
import ToolCallPill from './ToolCallPill.vue'
import type { Message } from '@/stores/chat'

const props = defineProps<{
  messages: Message[]
}>()

const threadContainer = ref<HTMLElement | null>(null)

// 智能合并工具调用与结果，防止冗余展示并改善交互体验
const mergedMessages = computed(() => {
  const list: any[] = []
  const resultByUseId = new Map<string, any>()
  
  // 查找所有的 tool_result 并用 map 存起来
  for (const msg of props.messages) {
    if (msg.role === 'tool_result' && msg.toolUseId) {
      resultByUseId.set(msg.toolUseId, msg)
    }
  }
  
  let activeSystemPrompt = ''
  let currentTurnThinking: string[] = []
  let currentTurnTools: any[] = []
  
  // 遍历消息流进行合并
  for (const msg of props.messages) {
    if (msg.role === 'system') {
      activeSystemPrompt = msg.content || ''
      continue
    }
    
    if (msg.role === 'user') {
      // 开启新的 Turn，清空本轮的推理链与工具链
      currentTurnThinking = []
      currentTurnTools = []
      list.push({
        type: 'user',
        content: msg.content
      })
      continue
    }
    
    if (msg.role === 'assistant_thinking') {
      if (msg.blocks && Array.isArray(msg.blocks)) {
        for (const block of msg.blocks) {
          if (block.type === 'thinking' && block.thinking) {
            currentTurnThinking.push(block.thinking)
          }
        }
      }
      continue
    }
    
    if (msg.role === 'assistant_tool_call') {
      const result = msg.toolUseId ? resultByUseId.get(msg.toolUseId) : null
      const toolObj = result
        ? {
            id: msg.toolUseId,
            type: 'tool',
            toolName: msg.toolName,
            input: msg.input,
            output: result.output,
            isError: result.isError,
            loading: false
          }
        : {
            id: msg.toolUseId || Math.random().toString(),
            type: 'tool',
            toolName: msg.toolName,
            input: msg.input,
            loading: true
          }
      
      currentTurnTools.push(toolObj)
      list.push(toolObj)
      continue
    }
    
    if (msg.role === 'tool_result') {
      // 已经被合并，不单独渲染
      continue
    }
    
    if (msg.role === 'assistant_progress') {
      list.push({
        type: 'progress',
        content: msg.content
      })
      continue
    }
    
    if (msg.role === 'assistant') {
      list.push({
        type: 'assistant',
        content: msg.content,
        isError: msg.isError,
        trace: {
          systemPrompt: activeSystemPrompt,
          thinking: currentTurnThinking.join('\n'),
          tools: [...currentTurnTools]
        }
      })
    }
  }
  
  return list
})

const scrollToBottom = () => {
  nextTick(() => {
    if (threadContainer.value) {
      // 采用更平滑的 scrollTop 直接置底，避免长对话中滚动迟钝
      threadContainer.value.scrollTop = threadContainer.value.scrollHeight
    }
  })
}

// 监听消息数组的变化并置底
watch(() => props.messages, scrollToBottom, { deep: true })

onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div
    ref="threadContainer"
    class="flex-grow overflow-y-auto terminal-scroll p-gutter md:p-margin-desktop w-full flex justify-center"
  >
    <div class="w-full max-w-[1024px] space-y-lg flex flex-col pb-8">
      <template v-for="(msg, index) in mergedMessages" :key="index">
        <!-- 用户提问气泡 -->
        <UserMessage
          v-if="msg.type === 'user'"
          :content="msg.content || ''"
        />
        
        <!-- AI 诊断卡片 (包装了辨证/方剂建议/安全提示组件，附带链路诊断面板) -->
        <AgentMessage
          v-else-if="msg.type === 'assistant'"
          :content="msg.content || ''"
          :is-error="msg.isError"
          :trace="msg.trace"
        />
        
        <!-- 工具调用小药丸 (支持展开查看 input/output) -->
        <ToolCallPill
          v-else-if="msg.type === 'tool'"
          :tool-name="msg.toolName || ''"
          :input="msg.input"
          :output="msg.output"
          :is-error="msg.isError"
          :loading="msg.loading"
        />
        
        <!-- 系统启动及环境信息流 -->
        <div
          v-else-if="msg.type === 'progress'"
          class="flex flex-col gap-xs mt-sm"
        >
          <div class="font-label-caps text-label-caps text-on-surface-variant flex items-center gap-xs select-none">
            <span class="text-primary opacity-50">SYSTEM_INIT</span>
            <span class="h-px w-4 bg-outline-variant"></span>
            <span>CLI MONITOR</span>
          </div>
          <div class="bg-surface-container-low p-sm rounded-sm border border-outline-variant border-l-2 border-l-surface-variant">
            <pre class="font-code-sm text-code-sm text-on-surface-variant opacity-80 whitespace-pre-wrap">{{ msg.content }}</pre>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
