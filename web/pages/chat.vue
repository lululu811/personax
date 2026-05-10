<template>
  <div class="flex flex-col h-full">
    <div class="px-4 py-3 bg-white border-b border-gray-200 flex items-center gap-2">
      <CommonPersonaAvatar :name="activePersona" :size="28" />
      <div>
        <div class="font-semibold text-sm">{{ personaDisplay }}</div>
      </div>
    </div>
    <ChatMessageList :messages="messages" :persona="activePersona" :loading="sending" />
    <ChatInput :loading="sending" @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const { token } = useAuth()
const config = useRuntimeConfig()
const activePersona = useState('activePersona', () => 'zettaranc')
const messages = useState<Array<{ role: string; content: string }>>('chatMessages', () => [])
const sending = ref(false)

const personaDisplay = computed(() => {
  const names: Record<string, string> = { zettaranc: 'Z哥', fupeng: '付鹏', boss_mo: 'BOSS墨', financial_analyst: '财务分析师' }
  return names[activePersona.value] || activePersona.value
})

async function handleSend(text: string) {
  messages.value.push({ role: 'user', content: text })
  sending.value = true
  try {
    const res = await $fetch<any>(`${config.public.apiBase}/api/v1/chat`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token.value}` },
      body: { query: text, persona: activePersona.value },
    })
    messages.value.push({ role: 'assistant', content: res.persona_analysis })
    useState('toolResults').value = res.tool_results || {}
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，分析出错了。请稍后重试。' })
  } finally {
    sending.value = false
  }
}
</script>
