<template>
  <aside class="w-[280px] bg-white border-l border-gray-200 p-4 overflow-y-auto">
    <h3 class="font-semibold mb-3 text-sm">📈 技术面板</h3>
    <div v-if="toolResults && Object.keys(toolResults).length > 0">
      <div
        v-for="(result, name) in toolResults"
        :key="name"
        class="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-2"
      >
        <div class="font-medium text-sm mb-2">{{ name }}</div>
        <div class="text-xs text-gray-600">{{ typeof result === 'object' ? JSON.stringify(result).slice(0, 100) : result }}</div>
      </div>
    </div>
    <div v-else class="text-sm text-gray-400 text-center py-8">
      发送消息后查看技术指标
    </div>
  </aside>
</template>

<script setup lang="ts">
const toolResults = useState<Record<string, any>>('toolResults', () => ({}))
</script>
