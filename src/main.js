import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'leaflet/dist/leaflet.css'
import App from './App.vue'
import router from './router.js'
import './style.css'
import { useAuthStore } from './stores/auth.js'
import { useSocialStore } from './stores/social.js'
import { useFavStore } from './stores/fav.js'
import { useFieldStore } from './stores/field.js'
import { useFriendsStore } from './stores/friends.js'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router)
app.mount('#app')

// 登录后拉云端数据（社区公开读，个人数据登录后拉）。OAuth 回调与验证码登录两条路都会走到
function loadUserData() {
  const social = useSocialStore(pinia)
  const fav = useFavStore(pinia)
  const field = useFieldStore(pinia)
  const friends = useFriendsStore(pinia)
  social.load()
  if (auth.isLogged) {
    fav
      .load()
      .then(() => field.load())
      .then(() => field.migrateLocalToCloud())
    field.ensureGear()
    friends.load()
  } else {
    friends.reset()
  }
}

// 启动引导：处理 OAuth 回调 / 恢复会话
const auth = useAuthStore(pinia)
auth
  .init()
  .then(loadUserData)
  .catch(() => {
    /* 网络异常：页面仍可用，云端功能显示对应错误 */
  })

// 验证码登录（手机 / 邮箱）在不刷新页面的情况下建立会话，由登录弹窗广播事件
window.addEventListener('yejing:auth-logged-in', loadUserData)

// 使用时长心跳：页面可见时每 60 秒上报一次，服务端函数累加进账号等级
setInterval(() => {
  if (document.visibilityState === 'visible') auth.heartbeat(60)
}, 60000)
