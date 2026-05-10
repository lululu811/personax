<template>
  <div
    class="rounded-full flex items-center justify-center text-white font-bold flex-shrink-0"
    :style="{ width: `${size}px`, height: `${size}px`, background: color, fontSize: `${size * 0.45}px` }"
  >
    {{ initial }}
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ name: string; size?: number }>()

const personaColors: Record<string, string> = {
  zettaranc: '#3b82f6', fupeng: '#10b981', boss_mo: '#f59e0b', financial_analyst: '#8b5cf6',
}
const personaInitials: Record<string, string> = {
  zettaranc: 'Z', fupeng: '付', boss_mo: 'B', financial_analyst: '财',
}

const color = computed(() => personaColors[props.name] || '#6b7280')
const initial = computed(() => personaInitials[props.name] || props.name[0])
const size = computed(() => props.size || 28)
</script>
