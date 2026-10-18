# 邻享生活前端

基于 Vue 3、TypeScript 和 Vite，包含消费者浏览/购物/订单与商家管理工作台。

## 本地运行

```sh
npm install
npm run dev
```

Vite 默认将 `/api` 请求代理到 `http://127.0.0.1:8000`。启动后端并确保其监听该地址即可联调。若后端地址不同，可在 `frontend/.env.local` 中设置：

```env
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

也可设置 `VITE_API_BASE_URL` 让浏览器直接请求 API；这种方式要求后端允许该前端源的跨域访问。环境变量示例见 `.env.example`。

## 检查与生产构建

```sh
npm run build
npm run preview
```

消费者 Token 与商家 Token 分别保存在浏览器本地存储中。模拟支付仅在后端开发环境显式开启后可用。
