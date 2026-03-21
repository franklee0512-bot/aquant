import axios from 'axios'

// 根据环境切换API地址
// 开发环境使用localhost，生产环境使用Railway地址
const baseURL = process.env.VUE_APP_API_URL || 'http://localhost:8000'

const request = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

export default request
