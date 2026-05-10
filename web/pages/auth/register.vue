<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-bold text-center mb-8">PersonaX</h1>
      <form @submit.prevent="handleRegister" class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-lg font-semibold mb-4">注册</h2>
        <div v-if="error" class="text-red-500 text-sm mb-3">{{ error }}</div>
        <input v-model="displayName" type="text" placeholder="昵称（可选）" class="w-full px-3 py-2 border rounded-md mb-3 text-sm" />
        <input v-model="email" type="email" placeholder="邮箱" class="w-full px-3 py-2 border rounded-md mb-3 text-sm" required />
        <input v-model="password" type="password" placeholder="密码（至少 6 位）" class="w-full px-3 py-2 border rounded-md mb-4 text-sm" minlength="6" required />
        <button type="submit" :disabled="loading" class="w-full bg-primary-600 text-white py-2 rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50">
          {{ loading ? '注册中...' : '注册' }}
        </button>
        <p class="text-center text-sm text-gray-500 mt-4">
          已有账号？<NuxtLink to="/auth/login" class="text-primary-600">登录</NuxtLink>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
const { register } = useAuth()
const email = ref('')
const password = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await register(email.value, password.value, displayName.value || undefined)
    navigateTo('/chat')
  } catch (e: any) {
    error.value = e?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>
