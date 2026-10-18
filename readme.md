# 邻享生活 NeighborShare

邻享生活是一个面向社区邻里的单店零售与外卖平台原型。消费者可以浏览邻享店铺、选购商品、维护收货地址和跟踪订单；商家经营者可以维护店铺、分类、商品、订单和经营数据。

本仓库包含 Vue 3 + TypeScript 前端和 FastAPI + SQLAlchemy 异步后端。本文聚焦项目的实际运行方式和**已实现功能**；接口业务细节见[后端业务接口设计](./后端业务接口.md)。

## 界面预览

### 消费者首页

![邻享生活消费者首页](./pictures/homepage.png)

### 消费者登录和订单

| 消费者登录 | 我的订单 |
| --- | --- |
| ![消费者登录窗口](./pictures/consumer-login.png) | ![消费者的我的订单页面](./pictures/orders.png) |

### 购物车与收货地址

![购物车、收货地址和下单入口](./pictures/shopping-cart.png)

### 商家入口与管理工作台

| 商家登录 | 商家工作台 |
| --- | --- |
| ![商家登录窗口](./pictures/merchant-login.png) | ![商家工作台：店铺、分类、商品、订单和统计示例](./pictures/merchant-dashboard.png) |

> 截图用于展示响应式界面。商品、订单和经营指标使用本地预览数据，不代表实际交易记录；实际内容以连接的后端数据库为准。

## 项目结构

```text
NeighborShare/
├── backend/
│   ├── app/
│   │   ├── common/       # ApiResponse 与全局异常响应
│   │   ├── config.py     # 配置及业务默认值
│   │   ├── db/           # 异步数据库、模型基类和 SQL 迁移
│   │   ├── dependencies/ # 消费者与商家身份鉴权
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── routers/      # FastAPI 路由
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── services/     # 业务逻辑
│   │   └── utils/        # 密码与 JWT 工具
│   ├── tests/            # pytest 异步 API 集成测试
│   ├── .env.example
│   ├── main.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/          # ApiResponse HTTP 客户端
│   │   ├── types/        # 前后端 API 类型
│   │   ├── App.vue       # 消费者和商家界面
│   │   └── style.css     # 响应式样式
│   ├── .env.example
│   └── package.json
├── pictures/             # README 界面截图
└── 后端业务接口.md        # 业务范围和接口契约
```

## 技术栈

| 部分 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite |
| 后端 | Python 3.13+、FastAPI、Pydantic v2 |
| 数据访问 | SQLAlchemy 异步 ORM；MySQL（aiomysql）或 SQLite（aiosqlite） |
| 身份认证 | 消费者与商家使用不同 `type` 的 JWT；密码采用 bcrypt 哈希 |
| 测试 | pytest、HTTPX、SQLite 内存数据库 |

## 功能范围

### 消费者前端

- 公开浏览固定的邻享店铺、商品分类和在售商品；按分类筛选商品。
- 消费者注册、登录与退出；Token 和账号资料保存在浏览器本地。
- 管理购物车及收货地址（新增、编辑、删除、设为默认）。
- 从购物车创建订单，查看本人订单并执行后端支持的取消、支付和确认收货操作。
- 商品价格、可售库存、店铺营业状态和订单金额由后端校验/计算；前端购物车金额只用于预览。

### 商家前端

- 商家账号注册/登录，与消费者账号及 Token 分开保存。
- 查看和编辑邻享店铺营业信息、配送范围、起送金额与配送费。
- 新增和删除商品分类；新增、编辑、删除商品以及上下架。
- 查看近期订单并按后端状态机推进订单状态。
- 查看今日/累计经营统计和热销商品排行。

### 后端现有 API

以下接口统一使用 `ApiResponse` 响应封装；管理员接口必须通过商家身份验证。

| 方法 | 路径 | 权限 | 功能 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | 公开 | 消费者注册 |
| `POST` | `/api/v1/auth/login` | 公开 | 消费者登录 |
| `GET` | `/api/v1/auth/me` | 消费者 | 查询当前账号 |
| `POST` | `/api/admin/auth/register` | 公开 | 商家账号注册 |
| `POST` | `/api/admin/auth/login` | 公开 | 商家登录 |
| `GET` | `/api/shop` | 公开 | 查询店铺信息 |
| `PUT` | `/api/shop` | 商家 | 更新店铺资料、营业状态及配送设置 |
| `GET` | `/api/categories` | 公开 | 查询商品分类 |
| `POST` | `/api/categories` | 商家 | 新增分类 |
| `PUT` / `DELETE` | `/api/categories/{category_id}` | 商家 | 编辑或删除分类 |
| `GET` | `/api/dishes` | 公开 | 查询在售商品；可选 `category_id` |
| `GET` | `/api/dishes/{dish_id}` | 公开 | 查询在售商品详情 |
| `GET` | `/api/admin/dishes` | 商家 | 查询所有商品 |
| `POST` | `/api/admin/dishes` | 商家 | 新增商品 |
| `PUT` / `DELETE` | `/api/admin/dishes/{dish_id}` | 商家 | 编辑或删除商品 |
| `PATCH` | `/api/admin/dishes/{dish_id}/availability` | 商家 | 上架或下架商品 |
| `GET` / `POST` | `/api/address` | 消费者 | 查询或新增本人地址 |
| `PUT` / `DELETE` | `/api/address/{address_id}` | 消费者 | 编辑或删除本人地址 |
| `PUT` | `/api/address/{address_id}/default` | 消费者 | 设置默认地址 |
| `GET` | `/api/cart` | 消费者 | 查询本人购物车 |
| `POST` | `/api/cart/items` | 消费者 | 加入商品 |
| `PUT` / `DELETE` | `/api/cart/items/{dish_id}` | 消费者 | 修改数量或移除商品 |
| `DELETE` | `/api/cart/items` | 消费者 | 清空购物车 |
| `POST` | `/api/orders` | 消费者 | 根据本人购物车和地址创建订单 |
| `GET` | `/api/orders` | 消费者 | 分页查询本人订单（默认 20 条，最多 100 条） |
| `GET` | `/api/orders/{order_id}` | 消费者 | 查询本人订单详情 |
| `POST` | `/api/orders/{order_id}/cancel` | 消费者 | 取消待支付订单 |
| `POST` | `/api/orders/{order_id}/pay` | 消费者 | 开发环境模拟支付（默认关闭） |
| `POST` | `/api/orders/{order_id}/confirm-receipt` | 消费者 | 确认配送中订单收货 |
| `GET` | `/api/admin/orders` | 商家 | 分页查询订单；可选 `status` |
| `PATCH` | `/api/admin/orders/{order_id}/status` | 商家 | 按状态机更新订单状态 |
| `GET` | `/api/admin/statistics/overview` | 商家 | 查询经营概览及商品排行 |

消费者订单列表和商家订单列表目前在 `data` 中直接返回数组；不能假设该响应已经使用 `{items, page, page_size, total}` 包装。参数和状态转换详情请以 [接口设计文档](./后端业务接口.md) 及 OpenAPI 为准。

新接口设计中提到的优惠券、秒杀、公开评价、商品收藏等属于规划能力，当前仓库尚未实现。真实支付渠道也尚未接入；模拟支付只允许在后端开发环境显式开启时使用。

## 开始使用

需要安装：

- Node.js `^22.18.0` 或 `>=24.12.0`、npm
- Python `>=3.13` 和 [uv](https://docs.astral.sh/uv/)
- MySQL（部署/多人开发推荐）或 SQLite（本地快速试用）

### 1. 配置并启动后端

在 PowerShell 中：

```powershell
Set-Location .\backend
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少设置数据库连接和 JWT 密钥：

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./neighborshare.db
JWT_SECRET_KEY=替换为长且随机的本地密钥
APP_ENV=development
ENABLE_SIMULATED_PAYMENTS=false
```

本地 SQLite 无需单独运行数据库服务。使用 MySQL 时，请根据实际数据库替换连接字符串，例如：

```dotenv
DATABASE_URL=mysql+aiomysql://用户名:密码@127.0.0.1:3306/neighborshare?charset=utf8mb4
```

安装后端依赖并启动 API：

```powershell
uv sync --dev
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

启动后端时，SQLAlchemy 会根据模型创建缺失的数据表，并确保固定店铺记录存在。已有数据库的手动建表迁移位于 `backend/app/db/migrations/`，应按编号顺序使用并先确认数据库备份。

接口文档：<http://127.0.0.1:8000/docs>

### 2. 配置并启动前端

另开一个终端：

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

打开 Vite 输出的本地地址（通常为 <http://127.0.0.1:5173>）。开发服务器会将 `/api` 请求代理到 `http://127.0.0.1:8000`。若后端运行在其他地址，可在 `frontend/.env.local` 中设置：

```dotenv
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

也可通过 `VITE_API_BASE_URL` 配置浏览器直接访问的 API 地址；此模式需要后端配置允许对应的跨域来源。

前后端配置示例分别见 [`backend/.env.example`](./backend/.env.example) 和 [`frontend/.env.example`](./frontend/.env.example)。不要把正式凭据提交到版本控制；任何 `VITE_` 前缀变量都会被打包到浏览器端，不得保存服务端密钥。

## 商家账号与模拟支付

商家可以通过商家登录入口创建独立商家账号。当前注册接口是公开注册：只应在可信网络或开发环境开放；部署到公网前应限制注册资格并加强管理端账号审批。

首次部署也可在 `backend/.env` 设置 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`，由应用启动时创建引导管理员。账号已存在时启动流程不会重置其密码。

模拟支付**默认关闭**。仅在明确用于本地开发测试时，才同时设置：

```dotenv
APP_ENV=development
ENABLE_SIMULATED_PAYMENTS=true
```

这只会更新本地订单状态，不会发起真实支付。生产环境必须保持禁用，不能将模拟支付结果当作真实到账。

## API 响应与权限约定

成功响应示例：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {}
}
```

错误响应示例：

```json
{
  "code": 404,
  "message": "订单不存在",
  "data": null
}
```

受保护接口使用：

```http
Authorization: Bearer <access_token>
```

消费者 Token 与商家 Token 相互隔离。前端隐藏管理入口不构成权限控制；后端会对用户/商家身份和资源归属进行验证。金额由服务端读取并计算，API 使用十进制金额字符串，不能信任客户端提交的金额。

## 检查与测试

运行后端测试（在 `backend` 目录）：

```powershell
uv run pytest -q
```

运行前端类型检查和生产构建（在 `frontend` 目录）：

```powershell
npm run build
```

构建产物位于 `frontend/dist/`；本地预览：

```powershell
npm run preview
```

## 部署前检查

- 配置生产数据库和强随机 JWT 密钥；保护 `.env`，不要提交或打印密钥。
- 使用 HTTPS，限制 CORS 来源，并通过反向代理只公开必要服务。
- 限制商家注册；创建和轮换管理员凭据。
- 生产环境关闭模拟支付；真实支付上线前实现可靠的渠道验签与支付状态回调。
- 规划中的优惠券/秒杀/评价/收藏等接口需在后端模型、事务、授权和测试落实后，才可对外宣称已提供。
- 配置数据库备份、错误日志与运行监控。
