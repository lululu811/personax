<template>
  <aside class="w-[200px] bg-slate-800 text-slate-300 flex flex-col h-full">
    <div class="p-4 font-bold text-white text-lg">PersonaX</div>
    <nav class="px-3 mb-4">
      <NuxtLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm mb-1"
        :class="$route.path === item.path ? 'bg-slate-700 text-white' : 'hover:bg-slate-700/50'"
      >
        <span>{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>
    <div class="px-3 mb-4">
      <div class="text-xs uppercase text-slate-500 mb-2 px-3">当前人格</div>
      <button
        v-for="p in personas"
        :key="p.name"
        class="flex items-center gap-2 px-3 py-2 rounded-md text-sm w-full mb-1"
        :class="p.name === activePersona ? 'bg-primary-600 text-white' : 'hover:bg-slate-700/50'"
        @click="activePersona = p.name"
      >
        <CommonPersonaAvatar :name="p.name" :size="20" />
        <span>{{ p.display_name }}</span>
      </button>
    </div>
    <div class="flex-1" />
    <div class="p-3 border-t border-slate-700">
      <NuxtLink to="/settings" class="flex items-center gap-2 text-sm hover:text-white">
        <div class="w-6 h-6 bg-slate-600 rounded-full" />
        <span>{{ user?.display_name || user?.email || '设置' }}</span>
      </NuxtLink>
    </div>
  </aside>
</template>

<script setup lang="ts">
const activePersona = useState('activePersona', () => 'zettaranc')
const user = useState<any>('user', () => null)
const config = useRuntimeConfig()

const navItems = [
  { path: '/chat', icon: '💬', label: '对话' },
  { path: '/chart/600519', icon: '📈', label: '图表' },
  { path: '/report/600519', icon: '📊', label: '财报分析' },
]

const personas = ref([
  { name: 'zettaranc', display_name: 'Z哥' },
  { name: 'fupeng', display_name: '付鹏' },
  { name: 'boss_mo', display_name: 'BOSS墨' },
  { name: 'financial_analyst', display_name: '财务分析师' },
])

// Try to fetch personas from API
try {
  const { data } = await useFetch<any[]>(`${config.public.apiBase}/api/v1/personas`, { default: () => [] })
  if (data.value && data.value.length > 0) {
    personas.value = data.value
  }
} catch {}
</script>
