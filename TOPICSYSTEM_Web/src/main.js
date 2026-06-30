import { createApp } from 'vue'
import './styles/tokens.css'   // 必须最先引入,后续 element-plus 主题会读 --el-color-primary
import './style.css'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
