export default defineNuxtRouteMiddleware((to) => {
  const token = useCookie('auth_token')
  if (!token.value && to.path !== '/auth/login' && to.path !== '/auth/register') {
    return navigateTo('/auth/login')
  }
})
