<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { storeToRefs } from 'pinia'

const store = useChatStore()
const { sessions, activeSessionId } = storeToRefs(store)

const createNew = () => {
  store.createNewSession()
}

const selectSession = (id: string) => {
  activeSessionId.value = id
}

const deleteSession = (id: string, event: Event) => {
  event.stopPropagation()
  store.deleteSession(id)
}
</script>

<template>
  <nav class="bg-surface-container-low border-r border-outline-variant h-full w-[280px] flex flex-col flex-shrink-0">
    <!-- Header -->
    <div class="px-gutter py-md border-b border-outline-variant flex items-center gap-sm">
      <span class="font-headline-md text-headline-md font-black text-primary">TCM-Agent</span>
      <span class="text-primary text-[16px]">⚕</span>
    </div>
    
    <!-- Version -->
    <div class="px-gutter py-sm">
      <p class="font-label-caps text-label-caps text-on-surface-variant uppercase mb-sm">Clinical Utility v1.0</p>
    </div>
    
    <!-- Session List -->
    <div class="flex-1 overflow-y-auto terminal-scroll px-sm py-sm space-y-xs">
      <div
        v-for="session in sessions"
        :key="session.id"
        @click="selectSession(session.id)"
        :class="[
          'w-full text-left px-sm py-sm rounded-sm transition-all flex items-center justify-between cursor-pointer group',
          activeSessionId === session.id
            ? 'bg-secondary-container text-on-secondary-container border-l-2 border-primary'
            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest'
        ]"
      >
        <div class="flex items-center gap-sm min-w-0">
          <span class="material-symbols-outlined text-[18px]">history</span>
          <span class="font-body-sm text-body-sm truncate pr-2">{{ session.title }}</span>
        </div>
        <button
          v-if="sessions.length > 1"
          @click="deleteSession(session.id, $event)"
          class="text-on-surface-variant hover:text-error opacity-0 group-hover:opacity-100 transition-opacity p-0.5"
          title="删除会话"
        >
          <span class="material-symbols-outlined text-[14px]">delete</span>
        </button>
      </div>
    </div>
    
    <!-- Footer Actions -->
    <div class="p-gutter border-t border-outline-variant space-y-sm">
      <button
        @click="createNew"
        class="w-full border border-primary text-primary hover:bg-primary/10 font-body-sm text-body-sm py-sm rounded-sm transition-colors flex items-center justify-center gap-xs cursor-pointer font-semibold"
      >
        <span class="material-symbols-outlined text-[16px]">add</span>
        New Chat
      </button>
      <div class="flex justify-between">
        <button class="text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer" title="设置">
          <span class="material-symbols-outlined text-[20px]">settings</span>
        </button>
        <button class="text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer" title="帮助">
          <span class="material-symbols-outlined text-[20px]">help</span>
        </button>
      </div>
    </div>
  </nav>
</template>
