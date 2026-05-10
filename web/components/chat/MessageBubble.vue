<template>
  <div class="flex gap-2" :class="message.role === 'user' ? 'flex-row-reverse' : ''">
    <div
      class="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs"
      :class="message.role === 'user' ? 'bg-gray-300' : 'bg-primary-500'"
    >
      {{ message.role === 'user' ? '' : personaInitial }}
    </div>
    <div
      class="px-3 py-2 rounded-xl text-sm max-w-[70%]"
      :class="message.role === 'user' ? 'bg-gray-100' : 'bg-blue-50 border border-blue-200'"
      v-html="renderedContent"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
const md = new MarkdownIt()
const props = defineProps<{ message: { role: string; content: string }; persona?: string }>()
const personaInitials: Record<string, string> = { zettaranc: 'Z', fupeng: '付', boss_mo: 'B', financial_analyst: '财' }
const personaInitial = computed(() => personaInitials[props.persona || 'zettaranc'] || 'Z')
const renderedContent = computed(() => md.render(props.message.content))
</script>
