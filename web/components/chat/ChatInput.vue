<template>
  <div class="p-4 bg-white border-t border-gray-200">
    <form @submit.prevent="send" class="flex gap-2 items-center">
      <input
        v-model="text"
        type="text"
        placeholder="输入你的问题..."
        class="flex-1 px-4 py-2 bg-gray-50 border border-gray-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
        :disabled="loading"
      />
      <button
        type="submit"
        :disabled="!text.trim() || loading"
        class="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white disabled:opacity-50 hover:bg-primary-600"
      >↑</button>
    </form>
  </div>
</template>

<script setup lang="ts">
defineProps<{ loading?: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()
const text = ref('')
function send() {
  if (text.value.trim()) {
    emit('send', text.value.trim())
    text.value = ''
  }
}
</script>
