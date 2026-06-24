import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import App from './App.vue'
import { installElementPlus } from './plugins/element-plus'
import router from './router'
import './assets/theme.css'

// 暗色为主：启用 Element Plus 暗色变量 + 本项目玻璃拟态主题
document.documentElement.classList.add('dark')

const app = createApp(App)

// 全局兜底：未被 ErrorBoundary 捕获的渲染错误、以及路由/懒加载错误，至少留下日志
app.config.errorHandler = (err, _instance, info) => {
  console.error('[全局错误]', info, err)
}
router.onError((err) => {
  console.error('[路由错误]', err)
})

app.use(createPinia())
app.use(router)
installElementPlus(app)
app.mount('#app')
