import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import { configureHttpNavigation } from './api/http'
import { useProjectAccess } from './composables/useProjectAccess'
import { router } from './router'
import './styles.css'

configureHttpNavigation({
  onUnauthorized: async (returnTo) => {
    if (router.currentRoute.value.name === 'login') return
    const redirect = returnTo.startsWith('/') && !returnTo.startsWith('//') ? returnTo : '/projects'
    await router.replace({ name: 'login', query: { redirect } })
  },
  onProjectArchived: () => {
    useProjectAccess().markCurrentProjectArchived()
  },
})

createApp(App)
  .use(ElementPlus, { locale: zhCn })
  .use(router)
  .mount('#app')
