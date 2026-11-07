import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 5178,
    host: '127.0.0.1'
  },
  build: {
    // 打成单文件 IIFE，dist/index.html 双击即可打开（file:// 下 ES module 会被 CORS 拦掉）
    rollupOptions: {
      output: {
        format: 'iife',
        inlineDynamicImports: true,
        // 带内容哈希：每次构建文件名都会变，浏览器不会再拿着旧 app.js 跑
        entryFileNames: 'assets/app-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
})
