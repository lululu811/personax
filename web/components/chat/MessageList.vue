<template>
  <div ref="listEl" class="flex-1 overflow-y-auto p-4 space-y-3">
    <ChatMessageBubble v-for="(msg, i) in messages" :key="i" :message="msg" :persona="persona" />
    <div v-if="loading" class="flex gap-2">
      <div class="w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center text-white text-xs">
        {{ personaInitial }}
      </div>
      <div class="bg-blue-50 border border-blue-200 px-3 py-2 rounded-xl text-sm">
        <span class="animate-pulse">思考中...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ messages: Array<{ role: string; content: string }>; persona?: string; loading?: boolean }>()
const listEl = ref<HTMLElement>()
const personaInitials: Record<string, string> = { zettaranc: 'Z', fupeng: '付', boss_mo: 'B', financial_analyst: '财' }
const personaInitial = computed(() => personaInitials[props.persona || 'zettaranc'] || 'Z')
watch(() => props.messages.length, () => {
  nextTick(() => { if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight })
})
</script>
