# 邻享生活 NeighborShare

邻享生活是一个单店零售与配送应用，包含消费者页面、商家工作台和 FastAPI 后端。消费者可以选购商品、管理地址和订单、领取优惠券及参加限量秒杀；商家可以维护商品、订单、优惠券和秒杀活动。

前端使用 Vue 3、TypeScript 和 Vite；后端使用 FastAPI、SQLAlchemy 异步 ORM 和 MySQL 或 SQLite。接口路径、参数和业务规则见[后端业务接口说明](./后端业务接口.md)。

## 功能

### 消费者

- 浏览店铺、商品分类、上架商品、可领取优惠券和秒杀活动。
- 注册、登录，管理购物车、收货地址和订单。
- 领取本人限额内的优惠券，在结算时使用一张符合门槛的立减券。
- 在活动时间内按库存和每人限购数量参加秒杀；成功后创建待支付订单。
- 取消待支付订单时，商品库存和秒杀名额会退回；已使用的优惠券也会恢复（若仍在有效期内）。

### 商家

- 管理店铺资料、商品分类、商品和订单。
- 创建、调整和停用优惠券；查看发行量及已领取数量。
- 创建、编辑、启用或停止秒杀活动；设置商品、秒杀价、活动库存、时间范围和每人限购数。
- 查看经营概览和商品销售排行。

## 优惠券与秒杀规则

- 优惠券采用固定金额立减，支持最低商品金额、总发行量、每人领取上限和有效期；每张订单只能使用一张。
- 店铺起送金额按优惠前的商品金额判断。优惠额不会超过商品金额，配送费不参与折扣。
- 停用优惠券会停止继续领取；已领到的券仍可在有效期内使用。优惠券已有领取记录后，面额、门槛和有效期不可修改。
- 秒杀订单不与优惠券叠加。秒杀成功后立即创建普通订单状态机中的“待支付”订单，不代表支付成功。
- 抢券和秒杀库存使用数据库条件更新及事务处理，限制数量、用户领取/购买上限和订单库存变化在数据库内校验；业务不依赖 Redis 或消息队列。
- 生产环境当前没有接入真实支付渠道，也没有未支付订单的自动超时关单任务。模拟支付仅用于显式开启的开发环境。

## 项目结构

```text
NeighborShare/
├── backend/
│   ├── app/
│   │   ├── common/       # 统一响应和异常处理
│   │   ├── db/migrations/# MySQL 与 SQLite SQL 迁移
│   │   ├── dependencies/ # 消费者和商家鉴权
│   │   ├── models/       # 数据模型
│   │   ├── routers/      # HTTP 接口
│   │   ├── schemas/      # 请求与响应校验
│   │   └── services/     # 订单、优惠券、秒杀等业务逻辑
│   ├── tests/            # API 集成测试
│   ├── .env.example
│   ├── main.py
│   └── pyproject.toml
├── frontend/
│   ├── src/App.vue       # 消费者页面和商家工作台
│   ├── src/api/          # HTTP 客户端
│   ├── src/types/        # API 数据类型
│   └── package.json
├── pictures/             # 页面截图
├── readme.md
└── 后端业务接口.md
```

## 本地运行

需要 Python 3.13 或更新版本、[uv](https://docs.astral.sh/uv/)、Node.js `^22.18.0` 或 `>=24.12.0` 及 npm。SQLite 可用于本地体验；部署或多人开发建议使用 MySQL。

### 启动后端

在 PowerShell 中：

```powershell
Set-Location .\backend
Copy-Item .env.example .env
```

编辑 `backend/.env`，设置数据库连接和随机 JWT 密钥。SQLite 示例：

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./neighborshare.db
JWT_SECRET_KEY=替换为长且随机的本地密钥
APP_ENV=development
ENABLE_SIMULATED_PAYMENTS=false
```

安装依赖并启动：

```powershell
uv sync --dev
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API 文档地址：<http://127.0.0.1:8000/docs>。

### 启动前端

另开一个 PowerShell 窗口：

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

打开 Vite 输出的地址，通常是 <http://127.0.0.1:5173>。开发代理默认指向 `http://127.0.0.1:8000`；需要更改时，在 `frontend/.env.local` 中设置 `VITE_API_PROXY_TARGET`。

## 数据库更新

新建数据库首次启动时，应用会按模型创建数据表。`Base.metadata.create_all` 不会修改已存在的表结构；升级已有数据库前先备份，并按数据库类型执行：

- MySQL：`backend/app/db/migrations/009_create_coupons_and_seckill.sql`
- SQLite：`backend/app/db/migrations/009_create_coupons_and_seckill_sqlite.sql`

这些脚本仅用于已经有旧版 NeighborShare 表结构的数据库，不要在首次创建的数据库上重复执行。应用启动后可通过商家工作台创建优惠券和秒杀活动。

## API 接口说明

后端默认地址为 `http://127.0.0.1:8000`，接口使用 JSON。消费者认证接口以 `/api/v1/auth` 为前缀，其余业务接口以 `/api` 为前缀。启动后可访问 <http://127.0.0.1:8000/docs> 查看 FastAPI 生成的交互式文档；下表列出当前已实现的接口。

### 认证、账号与权限

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | 公开 | 注册消费者，提交手机号和密码 |
| `POST` | `/api/v1/auth/login` | 公开 | 消费者登录并获取访问令牌 |
| `GET` | `/api/v1/auth/me` | 消费者 | 获取当前登录消费者 |
| `POST` | `/api/admin/auth/register` | 公开 | 注册商家账号 |
| `POST` | `/api/admin/auth/login` | 公开 | 商家登录并获取访问令牌 |

消费者注册使用 `phone` 和 `password` 字段，手机号须符合中国大陆手机号格式，密码至少 8 个字符。商家注册和登录使用 `username`、`password`。登录后在需要认证的请求中携带对应身份令牌：

```http
Authorization: Bearer <access_token>
```

消费者令牌不能用于商家接口，商家令牌也不能用于消费者接口。当前商家账号有公开注册入口，正式部署前应限制其注册资格。

### 店铺、分类和商品

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/shop` | 公开 | 获取店铺资料及营业、配送信息 |
| `PUT` | `/api/shop` | 商家 | 更新店铺和配送设置 |
| `GET` | `/api/categories` | 公开 | 查询商品分类 |
| `POST` | `/api/categories` | 商家 | 新增商品分类 |
| `PUT` | `/api/categories/{category_id}` | 商家 | 编辑商品分类 |
| `DELETE` | `/api/categories/{category_id}` | 商家 | 删除分类；分类下仍有关联商品时不能删除 |
| `GET` | `/api/dishes?category_id={id}` | 公开 | 查询上架商品；可按分类筛选 |
| `GET` | `/api/dishes/{dish_id}` | 公开 | 查询上架商品详情 |
| `GET` | `/api/admin/dishes` | 商家 | 查询商品；可按 `category_id`、`is_available` 筛选 |
| `POST` | `/api/admin/dishes` | 商家 | 新增商品 |
| `PUT` | `/api/admin/dishes/{dish_id}` | 商家 | 编辑商品资料 |
| `PATCH` | `/api/admin/dishes/{dish_id}/availability` | 商家 | 上架或下架商品 |
| `DELETE` | `/api/admin/dishes/{dish_id}` | 商家 | 删除商品 |

公开商品列表只返回上架商品；商家查询可查看下架商品。订单金额、商品价格和库存以服务端数据与计算结果为准，不接受客户端提交金额作为结算依据。

### 收货地址和购物车

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/address` | 消费者 | 查询本人收货地址 |
| `POST` | `/api/address` | 消费者 | 新增收货地址 |
| `PUT` | `/api/address/{address_id}` | 消费者 | 编辑本人地址 |
| `DELETE` | `/api/address/{address_id}` | 消费者 | 删除本人地址 |
| `PUT` | `/api/address/{address_id}/default` | 消费者 | 设为默认地址 |
| `GET` | `/api/cart` | 消费者 | 查询本人购物车 |
| `POST` | `/api/cart/items` | 消费者 | 加入商品，Body 包含 `dish_id`、`quantity` |
| `PUT` | `/api/cart/items/{dish_id}` | 消费者 | 修改商品数量，Body 包含 `quantity` |
| `DELETE` | `/api/cart/items/{dish_id}` | 消费者 | 移除购物车商品 |
| `DELETE` | `/api/cart/items` | 消费者 | 清空购物车 |

地址和购物车均按当前消费者隔离。完整字段和校验规则可在 `/docs` 查看。

### 订单与履约

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `POST` | `/api/orders` | 消费者 | 按购物车创建普通订单；可选使用一张优惠券 |
| `GET` | `/api/orders?page=1&page_size=20` | 消费者 | 分页查询本人订单 |
| `GET` | `/api/orders/{order_id}` | 消费者 | 查询本人订单详情 |
| `POST` | `/api/orders/{order_id}/cancel` | 消费者 | 取消待支付订单 |
| `POST` | `/api/orders/{order_id}/pay` | 消费者 | 开发环境模拟支付，不连接真实支付渠道 |
| `POST` | `/api/orders/{order_id}/confirm-receipt` | 消费者 | 确认收货 |
| `GET` | `/api/admin/orders?page=1&page_size=20` | 商家 | 分页查询订单；支持 `status` 筛选 |
| `PATCH` | `/api/admin/orders/{order_id}/status` | 商家 | 更新订单履约状态 |
| `GET` | `/api/admin/statistics/overview` | 商家 | 查询经营汇总和商品销售排行 |

普通订单创建 Body 示例：

```json
{
  "address_id": 12,
  "user_coupon_id": 34
}
```

`user_coupon_id` 可省略或设为 `null`。后端会验证地址归属、营业状态、起送金额、商品状态和库存，并保存商品及收货信息快照；客户端不提交订单金额或配送费。订单列表响应中的 `data` 是数组，分页通过 `page`、`page_size` 查询，不返回额外分页对象。

订单状态为 `pending_payment`（待支付）、`pending_acceptance`（待接单）、`pending_delivery`（配送中）、`completed`（已完成）和 `cancelled`（已取消）。正常履约顺序为待支付、待接单、配送中、已完成。消费者只能取消待支付订单；商家可按业务规则取消待接单或配送中订单。取消待支付订单会恢复商品库存，并按订单类型返还优惠券或秒杀名额。模拟支付需同时设置 `APP_ENV=development` 和 `ENABLE_SIMULATED_PAYMENTS=true`；项目未接入真实支付或未支付订单自动关单任务。

### 优惠券

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/coupons` | 公开 | 查询有效且仍可领取的优惠券 |
| `POST` | `/api/coupons/{coupon_id}/claim` | 消费者 | 领取优惠券；无需 Body |
| `GET` | `/api/users/me/coupons?status=available` | 消费者 | 查询本人优惠券；状态可为 `available`、`used` 或 `expired` |
| `GET` | `/api/admin/coupons` | 商家 | 查询优惠券及已领取数量 |
| `POST` | `/api/admin/coupons` | 商家 | 创建优惠券 |
| `PUT` | `/api/admin/coupons/{coupon_id}` | 商家 | 编辑优惠券 |
| `PATCH` | `/api/admin/coupons/{coupon_id}/active` | 商家 | 启用或停止继续发放 |

创建优惠券需提供 `name`、`discount_amount`、`total_quantity`、`start_time`、`end_time`；还可提供 `description`、`minimum_order_amount`、`per_user_limit` 和 `is_active`。时间使用 ISO 8601 格式；带时区值转换为 UTC，不带时区时按 UTC 处理。优惠券为固定金额立减券，一单最多使用一张；门槛按优惠前商品金额计算，配送费不参与抵扣，优惠额不超过商品金额。商家停发后，用户已领取的券仍可在有效期内使用；已有领取记录时不能修改优惠金额、门槛和有效期。

### 限量秒杀

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/seckill/activities` | 公开 | 查询即将开始或进行中的活动 |
| `GET` | `/api/seckill/activities/{activity_id}` | 公开 | 查询活动详情、状态和剩余名额 |
| `POST` | `/api/seckill/activities/{activity_id}/orders` | 消费者 | 参加秒杀并创建待支付订单 |
| `GET` | `/api/admin/seckill/activities` | 商家 | 查询全部活动 |
| `POST` | `/api/admin/seckill/activities` | 商家 | 创建活动 |
| `PUT` | `/api/admin/seckill/activities/{activity_id}` | 商家 | 编辑活动 |
| `PATCH` | `/api/admin/seckill/activities/{activity_id}/active` | 商家 | 启用或停止活动 |

秒杀下单 Body 示例：

```json
{
  "address_id": 12,
  "quantity": 1
}
```

创建活动需提供 `name`、`dish_id`、`sale_price`、`stock`、`limit_per_user`、`start_time`、`end_time`；`is_active` 可选。活动价格不得高于商品原价，活动库存不得超过当前商品库存。下单时后端校验活动时段、活动余量、每人限购、商品库存和店铺营业状态，并在同一数据库事务中扣减活动名额和商品库存。秒杀不与优惠券叠加；取消待支付秒杀订单时回补商品库存和活动已售数量。该流程由数据库事务处理，不依赖 Redis 或消息队列。

### 经营统计

`GET /api/admin/statistics/overview` 支持 `period=today|week|month|custom` 和 `top_n`（1 至 100）参数。使用 `period=custom` 时还需提供 `start_date=YYYY-MM-DD`、`end_date=YYYY-MM-DD`。响应包含所选周期及累计订单、收入和销量汇总，以及商品销售排行。

### 统一响应与错误

成功响应示例：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {}
}
```

创建类接口的 HTTP 状态码通常为 `201`，响应体中的 `code` 仍为 `200`。错误响应示例：

```json
{
  "code": 409,
  "message": "业务状态不允许该操作",
  "data": null
}
```

HTTP 状态码与错误响应中的 `code` 一致。常见状态包括：`401` 未认证或令牌类型错误、`404` 资源不存在或不属于当前用户、`409` 库存/限额/业务状态冲突、`422` 请求字段校验失败和 `500` 服务器内部错误。订单金额、优惠计算和关键库存检查均由服务端负责。

## 检查

在 `backend` 目录运行后端测试：

```powershell
uv run pytest -q
```

在 `frontend` 目录运行类型检查和生产构建：

```powershell
npm run build
```

## 预览图

截图用于展示页面布局，不代表线上交易数据。

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
| ![商家登录窗口](./pictures/merchant-login.png) | ![商家工作台：店铺、商品、订单和经营统计示例](./pictures/merchant-dashboard.png) |
