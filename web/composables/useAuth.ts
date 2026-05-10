export function useAuth() {
  const config = useRuntimeConfig()
  const token = useCookie('auth_token')
  const user = useState<any>('user', () => null)

  async function login(email: string, password: string) {
    const res = await $fetch<{ access_token: string }>(`${config.public.apiBase}/api/v1/auth/login`, {
      method: 'POST',
      body: { email, password },
    })
    token.value = res.access_token
    await fetchUser()
  }

  async function register(email: string, password: string, displayName?: string) {
    const res = await $fetch<{ access_token: string }>(`${config.public.apiBase}/api/v1/auth/register`, {
      method: 'POST',
      body: { email, password, display_name: displayName },
    })
    token.value = res.access_token
    await fetchUser()
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await $fetch(`${config.public.apiBase}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token.value}` },
      })
    } catch {
      token.value = null
      user.value = null
    }
  }

  function logout() {
    token.value = null
    user.value = null
    navigateTo('/auth/login')
  }

  return { user, token, login, register, fetchUser, logout, isLoggedIn: computed(() => !!token.value) }
}
