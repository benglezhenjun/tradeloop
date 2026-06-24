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

app.use(createPinia())
app.use(router)
installElementPlus(app)
app.mount('#app')
