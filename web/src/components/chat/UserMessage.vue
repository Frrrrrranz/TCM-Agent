<script setup lang="ts">
defineProps<{
  content: string
}>()
</script>

<template>
  <div class="self-end max-w-[85%] bg-surface-container-high border border-outline-variant p-md rounded-sm shadow-[2px_2px_0px_#1c1b1b]">
    <p class="font-body-md text-body-md leading-[1.7] text-on-surface whitespace-pre-wrap">
      {{ content }}
    </p>
  </div>
</template>
