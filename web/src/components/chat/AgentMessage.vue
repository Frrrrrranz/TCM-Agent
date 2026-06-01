<script setup lang="ts">
import { ref } from 'vue'
import DiagnosticBlock from './DiagnosticBlock.vue'

interface Trace {
  systemPrompt: string
  thinking: string
  tools: Array<{
    id: string
    toolName: string
    input: any
    output?: string
    isError?: boolean
    loading?: boolean
  }>
}

defineProps<{
  content: string
  isError?: boolean
  trace?: Trace
}>()

const isTraceOpen = ref(false)
const activeTab = ref(1) // 1: Prompt, 2: Thinking, 3: Tools
const openAccordions = ref<Record<string, boolean>>({})

const toggleTrace = () => {
  isTraceOpen.value = !isTraceOpen.value
}

const toggleAccordion = (id: string) => {
  openAccordions.value[id] = !openAccordions.value[id]
}
</script>

<template>
  <div
    :class="[
      'self-start w-full max-w-[90%] bg-surface-container-low border border-outline-variant p-md rounded-sm space-y-md shadow-[2px_2px_0px_#0e0e0e]',
      isError ? 'border-l-[3px] border-l-error' : 'border-l-[3px] border-l-primary'
    ]"
  >
    <!-- Header -->
    <div class="flex items-center gap-sm border-b border-outline-variant pb-xs mb-sm">
      <span class="text-primary text-[18px]">⚕</span>
      <span class="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-widest select-none">
        TCM-Agent Diagnostic
      </span>
    </div>
    
    <!-- Diagnostic Content Block -->
    <DiagnosticBlock :content="content" />

    <!-- ⚕ Execution Trace Panel -->
    <div v-if="trace && (trace.systemPrompt || trace.thinking || trace.tools.length > 0)" class="border border-outline-variant bg-surface-container rounded-sm overflow-hidden flex flex-col mt-md transition-all duration-300">
      <!-- Toolbar Header -->
      <div 
        @click="toggleTrace"
        class="flex justify-between items-center bg-surface-container-high px-md py-xs border-b border-outline-variant cursor-pointer group select-none"
      >
        <div class="flex items-center gap-sm">
          <span class="material-symbols-outlined text-primary text-[16px]">terminal</span>
          <h3 class="font-label-caps text-label-caps text-primary uppercase">⚕ Execution Diagnostics (执行链路诊断)</h3>
        </div>
        <button 
          class="font-label-caps text-label-caps text-on-surface-variant group-hover:text-primary transition-colors flex items-center gap-xs cursor-pointer"
        >
          <span class="material-symbols-outlined text-[14px]">{{ isTraceOpen ? 'remove' : 'add' }}</span>
          <span>{{ isTraceOpen ? 'HIDE TRACE CONSOLE' : 'SHOW TRACE CONSOLE' }}</span>
        </button>
      </div>

      <!-- Expandable Area -->
      <div v-show="isTraceOpen" class="flex flex-col">
        <!-- Tab Navigation -->
        <div class="flex border-b border-outline-variant bg-surface-container-low px-sm overflow-x-auto terminal-scroll relative">
          <button 
            @click="activeTab = 1"
            :class="[
              'px-md py-sm font-label-caps text-label-caps transition-colors whitespace-nowrap cursor-pointer border-b-2',
              activeTab === 1 ? 'text-primary border-primary glow-text' : 'text-on-surface-variant hover:text-on-surface border-transparent'
            ]"
          >
            <span class="mr-xs">🔍</span>Prompt Detector (提示词探测)
          </button>
          <button 
            @click="activeTab = 2"
            :class="[
              'px-md py-sm font-label-caps text-label-caps transition-colors whitespace-nowrap cursor-pointer border-b-2',
              activeTab === 2 ? 'text-primary border-primary glow-text' : 'text-on-surface-variant hover:text-on-surface border-transparent'
            ]"
          >
            <span class="mr-xs">🧠</span>Reasoning Chain (思维推理链)
          </button>
          <button 
            @click="activeTab = 3"
            :class="[
              'px-md py-sm font-label-caps text-label-caps transition-colors whitespace-nowrap cursor-pointer border-b-2',
              activeTab === 3 ? 'text-primary border-primary glow-text' : 'text-on-surface-variant hover:text-on-surface border-transparent'
            ]"
          >
            <span class="mr-xs">🛠️</span>MCP & RAG Tools Trace
          </button>
        </div>

        <!-- Content Area -->
        <div class="h-[300px] bg-surface-container-lowest p-md overflow-y-auto terminal-scroll font-code-sm text-code-sm">
          
          <!-- Tab 1: Prompt Detector -->
          <div v-show="activeTab === 1" class="space-y-sm">
            <div class="bg-surface-container border border-outline-variant rounded p-sm relative">
              <div class="absolute top-2 right-2 flex gap-xs select-none">
                <span class="w-2.5 h-2.5 rounded-full bg-outline-variant"></span>
                <span class="w-2.5 h-2.5 rounded-full bg-outline-variant"></span>
              </div>
              <span class="text-tertiary font-semibold block mb-xs"># SYSTEM_INSTRUCTION_BLOCK</span>
              <pre class="text-on-surface-variant whitespace-pre-wrap leading-[1.6] select-all max-h-[220px] overflow-y-auto terminal-scroll">{{ trace.systemPrompt || 'No system prompt recorded.' }}</pre>
            </div>
          </div>

          <!-- Tab 2: Reasoning Chain -->
          <div v-show="activeTab === 2" class="space-y-xs text-primary opacity-90 leading-[1.6]">
            <p v-if="!trace.thinking" class="text-outline font-semibold">No reasoning chain captured for this turn.</p>
            <template v-else>
              <p class="text-outline select-none font-semibold">[11:27:58.000] Initializing cognitive trace...</p>
              <pre class="whitespace-pre-wrap text-primary-fixed-dim font-code-sm leading-relaxed">{{ trace.thinking }}<span class="ml-1 blink">_</span></pre>
            </template>
          </div>

          <!-- Tab 3: Tools Trace -->
          <div v-show="activeTab === 3">
            <p v-if="trace.tools.length === 0" class="text-on-surface-variant opacity-60">No tools called in this turn.</p>
            <div v-else class="relative pl-md border-l border-outline-variant space-y-md ml-xs py-xs">
              <div 
                v-for="(tool, index) in trace.tools" 
                :key="tool.id || index"
                class="relative timeline-node"
              >
                <!-- Dot node -->
                <div 
                  :class="[
                    'absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full border border-background ring-1 ring-outline-variant',
                    tool.loading 
                      ? 'bg-amber-500 animate-pulse ring-amber-500/50' 
                      : tool.isError 
                        ? 'bg-error ring-error/50 shadow-[0_0_6px_#ffb4ab]' 
                        : 'bg-primary ring-primary/50 shadow-[0_0_6px_#83d7b5]'
                  ]"
                ></div>

                <div class="flex items-center gap-xs flex-wrap">
                  <span 
                    :class="[
                      'px-sm py-0.5 rounded-sm font-label-caps text-label-caps',
                      tool.loading 
                        ? 'bg-amber-500/20 text-amber-500 border border-amber-500/30' 
                        : tool.isError 
                          ? 'bg-error-container/20 text-error border border-error/30' 
                          : 'bg-primary-container/20 text-primary border border-primary/30 shadow-[0_0_6px_rgba(131,215,181,0.2)]'
                    ]"
                  >
                    {{ tool.loading ? 'CALLING' : tool.isError ? 'FAILED' : 'PASSED' }}
                  </span>
                  <span class="text-on-surface">`{{ tool.toolName }}`</span>
                </div>

                <!-- Input/Output Expandable -->
                <div class="bg-surface-container-low border border-outline-variant rounded mt-sm">
                  <button 
                    @click="toggleAccordion(tool.id)"
                    class="w-full text-left px-sm py-xs text-code-sm text-on-surface-variant flex justify-between items-center hover:bg-surface-container-highest transition-colors select-none"
                  >
                    <span class="truncate">Input: {{ JSON.stringify(tool.input) }}</span>
                    <span 
                      class="material-symbols-outlined text-[14px] transition-transform duration-200" 
                      :style="{ transform: openAccordions[tool.id] ? 'rotate(180deg)' : 'rotate(0deg)' }"
                    >
                      expand_more
                    </span>
                  </button>
                  <div 
                    v-show="openAccordions[tool.id]"
                    class="px-sm py-xs border-t border-outline-variant text-code-sm text-on-surface"
                  >
                    <span class="text-secondary opacity-60 font-semibold block mb-xs">&gt; Output:</span>
                    <pre class="whitespace-pre-wrap text-secondary font-code-sm bg-surface-container-lowest p-xs rounded-sm max-h-[160px] overflow-y-auto terminal-scroll">{{ tool.output || 'No output returned.' }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

  </div>
</template>
