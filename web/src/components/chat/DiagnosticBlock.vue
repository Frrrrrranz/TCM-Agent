<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const parsedSections = computed(() => {
  const text = props.content || ''
  
  let diagnosis = ''
  let formula = ''
  let safety = ''
  
  // 使用正则匹配中文块标示：支持包含括号、英文的混合写法
  const regex = /【(辨证结果|方剂建议|经典方剂|安全提示)】[^\n]*\n?/g
  
  // 查找各个块的起始位置
  const matches: { title: string; index: number; textLength: number }[] = []
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match[1]) {
      matches.push({
        title: match[1],
        index: match.index,
        textLength: match[0].length
      })
    }
  }
  
  if (matches.length === 0) {
    // 兜底：如果完全没有这些标记，则整段都归入辨证结果
    diagnosis = text
  } else {
    // 排序后按段提取内容
    for (let i = 0; i < matches.length; i++) {
      const current = matches[i]
      if (!current) continue
      const start = current.index + current.textLength
      const nextMatch = i + 1 < matches.length ? matches[i + 1] : null
      const end = nextMatch ? nextMatch.index : text.length
      const blockText = text.substring(start, end).trim()
      
      if (current.title.includes('辨证')) {
        diagnosis = blockText
      } else if (current.title.includes('方剂') || current.title.includes('经典')) {
        formula = blockText
      } else if (current.title.includes('安全')) {
        safety = blockText
      }
    }
  }
  
  return { diagnosis, formula, safety }
})
</script>

<template>
  <div class="space-y-md">
    <!-- 辨证结果 -->
    <div v-if="parsedSections.diagnosis" class="space-y-xs">
      <h3 class="font-label-caps text-label-caps text-primary uppercase">【辨证结果】</h3>
      <p class="font-body-md text-body-md leading-[1.7] pl-md border-l border-outline-variant text-on-surface whitespace-pre-wrap">
        {{ parsedSections.diagnosis }}
      </p>
    </div>

    <!-- 方剂建议 (可折叠) -->
    <details
      v-if="parsedSections.formula"
      class="group border border-outline-variant rounded-sm bg-surface-container-lowest"
      open
    >
      <summary class="flex items-center justify-between p-sm cursor-pointer hover:bg-surface-container-highest transition-colors font-label-caps text-label-caps text-secondary uppercase list-none select-none">
        <span>【方剂建议】</span>
        <span class="material-symbols-outlined group-open:rotate-180 transition-transform text-[16px] flex items-center">expand_more</span>
      </summary>
      <div class="p-sm border-t border-outline-variant font-body-md text-body-md leading-[1.7] text-on-surface whitespace-pre-wrap">
        {{ parsedSections.formula }}
      </div>
    </details>

    <!-- 安全提示 (可折叠且红色高亮) -->
    <details
      v-if="parsedSections.safety"
      class="group border border-outline-variant rounded-sm bg-surface-container-lowest"
      open
    >
      <summary class="flex items-center justify-between p-sm cursor-pointer hover:bg-surface-container-highest transition-colors font-label-caps text-label-caps text-error uppercase list-none select-none">
        <span>【安全提示】</span>
        <span class="material-symbols-outlined group-open:rotate-180 transition-transform text-[16px] flex items-center">expand_more</span>
      </summary>
      <div class="p-sm border-t border-outline-variant font-body-md text-body-md leading-[1.7] text-error-container whitespace-pre-wrap">
        {{ parsedSections.safety }}
      </div>
    </details>
  </div>
</template>
