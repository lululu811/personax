<template>
  <div class="flex h-screen bg-gray-50">
    <LayoutAppSidebar />
    <main class="flex-1 flex flex-col overflow-hidden">
      <slot />
    </main>
    <LayoutAppRightPanel />
  </div>
</template>
