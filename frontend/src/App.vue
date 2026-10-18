<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ApiError, get, patch, post, put, remove } from '@/api/http'
import type {
  Address,
  Admin,
  Cart,
  Category,
  Coupon,
  Dish,
  LoginData,
  Order,
  OrderStatus,
  SeckillActivity,
  Shop,
  Statistics,
  User,
  UserCoupon,
} from '@/types/api'

type View = 'discover' | 'orders' | 'merchant'
type AuthMode = 'login' | 'register'

const userToken = ref(localStorage.getItem('neighborshare.userToken') ?? '')
const adminToken = ref(localStorage.getItem('neighborshare.adminToken') ?? '')
const user = ref<User | null>(readStored<User>('neighborshare.user'))
const admin = ref<Admin | null>(readStored<Admin>('neighborshare.admin'))
const shop = ref<Shop | null>(null)
const categories = ref<Category[]>([])
const dishes = ref<Dish[]>([])
const cart = ref<Cart>({ items: [], total_quantity: 0, total_amount: '0.00' })
const addresses = ref<Address[]>([])
const orders = ref<Order[]>([])
const adminOrders = ref<Order[]>([])
const coupons = ref<Coupon[]>([])
const userCoupons = ref<UserCoupon[]>([])
const seckillActivities = ref<SeckillActivity[]>([])
const adminCoupons = ref<Coupon[]>([])
const adminSeckillActivities = ref<SeckillActivity[]>([])
const statistics = ref<Statistics | null>(null)
const activeView = ref<View>('discover')
const activeCategory = ref<number | null>(null)
const authMode = ref<AuthMode>('login')
const authRole = ref<'user' | 'admin'>('user')
const authDialog = ref(false)
const addressDialog = ref(false)
const busy = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const selectedAddressId = ref<number | null>(null)
const selectedUserCouponId = ref<number | null>(null)
const editingAddressId = ref<number | null>(null)
const authForm = reactive({ phone: '', username: '', password: '' })
const addressForm = reactive({
  recipient_name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
})
const dishForm = reactive({
  name: '',
  image_url: '',
  price: '',
  stock: 0,
  description: '',
  category_id: 0,
})
const editingDishId = ref<number | null>(null)
const editingCouponId = ref<number | null>(null)
const editingSeckillActivityId = ref<number | null>(null)
const categoryName = ref('')
const couponForm = reactive({
  name: '',
  description: '',
  discount_amount: '',
  minimum_order_amount: '0',
  total_quantity: 1,
  per_user_limit: 1,
  start_time: localDateTime(0),
  end_time: localDateTime(24),
})
const seckillForm = reactive({
  name: '',
  dish_id: 0,
  sale_price: '',
  stock: 1,
  limit_per_user: 1,
  start_time: localDateTime(0),
  end_time: localDateTime(1),
})

const visibleDishes = computed(() =>
  activeCategory.value === null
    ? dishes.value
    : dishes.value.filter((dish) => dish.category_id === activeCategory.value),
)
const loggedIn = computed(() => Boolean(userToken.value && user.value))
const merchantLoggedIn = computed(() => Boolean(adminToken.value && admin.value))
const cartItemsCount = computed(() => cart.value.total_quantity)
const activeAddress = computed(() =>
  addresses.value.find((address) => address.id === selectedAddressId.value),
)
const availableUserCoupons = computed(() =>
  userCoupons.value.filter((userCoupon) => userCoupon.status === 'available'),
)
const selectedUserCoupon = computed(() =>
  availableUserCoupons.value.find(
    (userCoupon) => userCoupon.id === selectedUserCouponId.value,
  ),
)
const editingCouponHasClaims = computed(() =>
  adminCoupons.value.some(
    (coupon) =>
      coupon.id === editingCouponId.value && coupon.claimed_quantity > 0,
  ),
)
const couponDiscountPreview = computed(() => {
  const userCoupon = selectedUserCoupon.value
  if (
    !userCoupon ||
    Number(cart.value.total_amount) < Number(userCoupon.coupon.minimum_order_amount)
  ) {
    return 0
  }
  return Math.min(
    Number(cart.value.total_amount),
    Number(userCoupon.coupon.discount_amount),
  )
})
const checkoutTotalPreview = computed(() =>
  Math.max(
    0,
    Number(cart.value.total_amount) -
      couponDiscountPreview.value +
      Number(shop.value?.delivery_fee ?? 0),
  ),
)

function localDateTime(hoursFromNow: number) {
  const date = new Date(Date.now() + hoursFromNow * 60 * 60 * 1000)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function apiDateTime(value: string) {
  return new Date(value).toISOString()
}

function inputDateTime(value: string) {
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function readStored<T>(key: string): T | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? 'null')
    return value && typeof value === 'object' ? (value as T) : null
  } catch {
    return null
  }
}

function notify(message: string, success = false) {
  errorMessage.value = success ? '' : message
  successMessage.value = success ? message : ''
  window.setTimeout(() => {
    if (errorMessage.value === message) errorMessage.value = ''
    if (successMessage.value === message) successMessage.value = ''
  }, 3800)
}

async function run<T>(action: () => Promise<T>): Promise<T | null> {
  busy.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    return await action()
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) clearExpiredSession()
      notify(error.message)
    } else {
      notify(error instanceof Error ? error.message : '操作失败，请稍后重试')
    }
    return null
  } finally {
    busy.value = false
  }
}

function clearExpiredSession() {
  if (activeView.value === 'merchant') logout('admin')
  else logout('user')
}

function saveSession(role: 'user' | 'admin', token: string, identity: User | Admin) {
  if (role === 'user') {
    userToken.value = token
    user.value = identity as User
    localStorage.setItem('neighborshare.userToken', token)
    localStorage.setItem('neighborshare.user', JSON.stringify(identity))
  } else {
    adminToken.value = token
    admin.value = identity as Admin
    localStorage.setItem('neighborshare.adminToken', token)
    localStorage.setItem('neighborshare.admin', JSON.stringify(identity))
  }
}

function logout(role: 'user' | 'admin') {
  if (role === 'user') {
    userToken.value = ''
    user.value = null
    cart.value = { items: [], total_quantity: 0, total_amount: '0.00' }
    addresses.value = []
    orders.value = []
    userCoupons.value = []
    selectedUserCouponId.value = null
    localStorage.removeItem('neighborshare.userToken')
    localStorage.removeItem('neighborshare.user')
  } else {
    adminToken.value = ''
    admin.value = null
    adminOrders.value = []
    statistics.value = null
    localStorage.removeItem('neighborshare.adminToken')
    localStorage.removeItem('neighborshare.admin')
  }
  if (!userToken.value && !adminToken.value) activeView.value = 'discover'
}

async function loadPublicData() {
  const results = await Promise.all([
    get<Shop>('/api/shop'),
    get<Category[]>('/api/categories'),
    get<Dish[]>('/api/dishes'),
    get<Coupon[]>('/api/coupons'),
    get<SeckillActivity[]>('/api/seckill/activities'),
  ])
  shop.value = results[0]
  categories.value = results[1]
  dishes.value = results[2]
  coupons.value = results[3]
  seckillActivities.value = results[4]
}

async function loadCart() {
  if (!userToken.value) return
  const result = await run(() => get<Cart>('/api/cart', userToken.value))
  if (result) cart.value = result
}

async function loadUserData() {
  if (!userToken.value) return
  await Promise.all([
    loadCart(),
    (async () => {
      const result = await run(() => get<Address[]>('/api/address', userToken.value))
      if (result) {
        addresses.value = result
        selectedAddressId.value =
          result.find((address) => address.is_default)?.id ?? result[0]?.id ?? null
      }
    })(),
    (async () => {
      const result = await run(() => get<Order[]>('/api/orders', userToken.value))
      if (result) orders.value = result
    })(),
    (async () => {
      const result = await run(() =>
        get<UserCoupon[]>('/api/users/me/coupons', userToken.value),
      )
      if (result) {
        userCoupons.value = result
        if (!result.some((item) => item.id === selectedUserCouponId.value)) {
          selectedUserCouponId.value = null
        }
      }
    })(),
  ])
}

async function loadMerchantData() {
  if (!adminToken.value) return
  const results = await Promise.all([
    run(() => get<Order[]>('/api/admin/orders', adminToken.value)),
    run(() => get<Statistics>('/api/admin/statistics/overview', adminToken.value)),
    run(() =>
      get<Dish[]>('/api/admin/dishes', adminToken.value),
    ),
    run(() => get<Coupon[]>('/api/admin/coupons', adminToken.value)),
    run(() =>
      get<SeckillActivity[]>(
        '/api/admin/seckill/activities',
        adminToken.value,
      ),
    ),
  ])
  if (results[0]) adminOrders.value = results[0]
  if (results[1]) statistics.value = results[1]
  if (results[2]) dishes.value = results[2]
  if (results[3]) adminCoupons.value = results[3]
  if (results[4]) adminSeckillActivities.value = results[4]
  const firstDish = dishes.value[0]
  if (seckillForm.dish_id === 0 && firstDish) {
    seckillForm.dish_id = firstDish.id
  }
}

function openAuth(role: 'user' | 'admin', mode: AuthMode = 'login') {
  authRole.value = role
  authMode.value = mode
  authDialog.value = true
}

async function submitAuth() {
  const role = authRole.value
  const root = role === 'user' ? '/api/v1/auth' : '/api/admin/auth'
  const body =
    role === 'user'
      ? { phone: authForm.phone, password: authForm.password }
      : { username: authForm.username, password: authForm.password }
  if (authMode.value === 'register') {
    const created = await run(() =>
      post<User>(`${root}/register`, body),
    )
    if (!created) return
    if (role === 'user') authForm.phone = ''
    notify('注册成功，请登录', true)
    authMode.value = 'login'
    return
  }
  const result = await run(() => post<LoginData<User | Admin>>(`${root}/login`, body))
  if (!result) return
  const identity = role === 'user' ? result.user : result.admin
  if (!identity) {
    notify('登录响应缺少账号信息')
    return
  }
  saveSession(role, result.access_token, identity)
  authDialog.value = false
  notify('欢迎回来', true)
  if (role === 'user') await loadUserData()
  else {
    activeView.value = 'merchant'
    await loadMerchantData()
  }
}

async function addToCart(dish: Dish) {
  if (!loggedIn.value) {
    openAuth('user')
    return
  }
  const result = await run(() =>
    post<Cart>(
      '/api/cart/items',
      { dish_id: dish.id, quantity: 1 },
      userToken.value,
    ),
  )
  if (result) {
    cart.value = result
    notify(`${dish.name} 已加入购物车`, true)
  }
}

async function claimCoupon(coupon: Coupon) {
  if (!loggedIn.value) {
    openAuth('user')
    return
  }
  const claimed = await run(() =>
    post<UserCoupon>(
      `/api/coupons/${coupon.id}/claim`,
      undefined,
      userToken.value,
    ),
  )
  if (!claimed) return
  userCoupons.value.unshift(claimed)
  await run(loadPublicData)
  notify('优惠券已放入你的卡包', true)
}

async function buySeckill(activity: SeckillActivity) {
  if (!loggedIn.value) {
    openAuth('user')
    return
  }
  if (!selectedAddressId.value) {
    openAddressDialog()
    notify('请先添加收货地址，再参与秒杀')
    return
  }
  const order = await run(() =>
    post<Order>(
      `/api/seckill/activities/${activity.id}/orders`,
      { address_id: selectedAddressId.value, quantity: 1 },
      userToken.value,
    ),
  )
  if (!order) return
  orders.value.unshift(order)
  activeView.value = 'orders'
  await run(loadPublicData)
  notify('秒杀成功，订单已创建', true)
}

async function setQuantity(dishId: number, quantity: number) {
  if (!userToken.value) return
  if (quantity < 1) {
    const result = await run(() =>
      remove(`/api/cart/items/${dishId}`, userToken.value),
    )
    if (result !== null) await loadCart()
    return
  }
  const result = await run(() =>
    put<Cart>(`/api/cart/items/${dishId}`, { quantity }, userToken.value),
  )
  if (result) cart.value = result
}

function openAddressDialog() {
  if (!loggedIn.value) {
    openAuth('user')
    return
  }
  editingAddressId.value = null
  Object.assign(addressForm, {
    recipient_name: '',
    phone: '',
    province: '',
    city: '',
    district: '',
    detail: '',
  })
  addressDialog.value = true
}

function editAddress(address: Address) {
  editingAddressId.value = address.id
  Object.assign(addressForm, {
    recipient_name: address.recipient_name,
    phone: address.phone,
    province: address.province,
    city: address.city,
    district: address.district,
    detail: address.detail,
  })
  addressDialog.value = true
}

async function addAddress() {
  const result = editingAddressId.value
    ? await run(() =>
        put<Address>(
          `/api/address/${editingAddressId.value}`,
          addressForm,
          userToken.value,
        ),
      )
    : await run(() =>
        post<Address>(
          '/api/address',
          { ...addressForm, is_default: addresses.value.length === 0 },
          userToken.value,
        ),
      )
  if (!result) return
  const existingIndex = addresses.value.findIndex((address) => address.id === result.id)
  if (existingIndex >= 0) addresses.value[existingIndex] = result
  else addresses.value.unshift(result)
  selectedAddressId.value = result.id
  addressDialog.value = false
  editingAddressId.value = null
  Object.assign(addressForm, {
    recipient_name: '',
    phone: '',
    province: '',
    city: '',
    district: '',
    detail: '',
  })
}

async function setDefaultAddress(address: Address) {
  const result = await run(() =>
    put<Address>(`/api/address/${address.id}/default`, {}, userToken.value),
  )
  if (!result) return
  addresses.value = addresses.value.map((item) => ({
    ...item,
    is_default: item.id === result.id,
  }))
  selectedAddressId.value = result.id
}

async function deleteAddress(address: Address) {
  if (!window.confirm(`确定删除 ${address.recipient_name} 的收货地址吗？`)) return
  const deleted = await run(() =>
    remove(`/api/address/${address.id}`, userToken.value),
  )
  if (deleted === null) return
  const result = await run(() => get<Address[]>('/api/address', userToken.value))
  if (!result) return
  addresses.value = result
  selectedAddressId.value =
    result.find((item) => item.is_default)?.id ?? result[0]?.id ?? null
}

async function checkout() {
  if (!cart.value.items.length) return
  if (!selectedAddressId.value) {
    openAddressDialog()
    return
  }
  const order = await run(() =>
    post<Order>(
      '/api/orders',
      {
        address_id: selectedAddressId.value,
        user_coupon_id: selectedUserCouponId.value,
      },
      userToken.value,
    ),
  )
  if (!order) return
  orders.value.unshift(order)
  const cleared = await run(() =>
    remove('/api/cart/items', userToken.value),
  )
  if (cleared === null) {
    activeView.value = 'orders'
    notify('订单已创建，但购物袋清空失败；请刷新购物袋确认商品状态')
    return
  }
  cart.value = { items: [], total_quantity: 0, total_amount: '0.00' }
  selectedUserCouponId.value = null
  await loadUserData()
  notify('订单创建成功，请在订单中完成支付', true)
  activeView.value = 'orders'
}

async function createCoupon() {
  const editingCoupon = adminCoupons.value.find(
    (coupon) => coupon.id === editingCouponId.value,
  )
  const common = {
    name: couponForm.name,
    description: couponForm.description || null,
    total_quantity: Number(couponForm.total_quantity),
    per_user_limit: Number(couponForm.per_user_limit),
  }
  const payload =
    editingCoupon && editingCoupon.claimed_quantity > 0
      ? common
      : {
          ...common,
          discount_amount: Number(couponForm.discount_amount),
          minimum_order_amount: Number(couponForm.minimum_order_amount),
          start_time: apiDateTime(couponForm.start_time),
          end_time: apiDateTime(couponForm.end_time),
        }
  const wasEditing = editingCouponId.value !== null
  const result = editingCouponId.value
    ? await run(() =>
        put<Coupon>(
          `/api/admin/coupons/${editingCouponId.value}`,
          payload,
          adminToken.value,
        ),
      )
    : await run(() =>
        post<Coupon>('/api/admin/coupons', payload, adminToken.value),
      )
  if (!result) return
  const index = adminCoupons.value.findIndex((item) => item.id === result.id)
  if (index >= 0) adminCoupons.value[index] = result
  else adminCoupons.value.unshift(result)
  editingCouponId.value = null
  couponForm.name = ''
  couponForm.description = ''
  couponForm.discount_amount = ''
  couponForm.start_time = localDateTime(0)
  couponForm.end_time = localDateTime(24)
  notify(wasEditing ? '优惠券已更新' : '优惠券已创建', true)
}

function editCoupon(coupon: Coupon) {
  editingCouponId.value = coupon.id
  Object.assign(couponForm, {
    name: coupon.name,
    description: coupon.description ?? '',
    discount_amount: coupon.discount_amount,
    minimum_order_amount: coupon.minimum_order_amount,
    total_quantity: coupon.total_quantity,
    per_user_limit: coupon.per_user_limit,
    start_time: inputDateTime(coupon.start_time),
    end_time: inputDateTime(coupon.end_time),
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function cancelCouponEdit() {
  editingCouponId.value = null
  Object.assign(couponForm, {
    name: '',
    description: '',
    discount_amount: '',
    minimum_order_amount: '0',
    total_quantity: 1,
    per_user_limit: 1,
    start_time: localDateTime(0),
    end_time: localDateTime(24),
  })
}

async function toggleCoupon(coupon: Coupon) {
  const result = await run(() =>
    patch<Coupon>(
      `/api/admin/coupons/${coupon.id}/active`,
      { is_active: !coupon.is_active },
      adminToken.value,
    ),
  )
  if (result) {
    const index = adminCoupons.value.findIndex((item) => item.id === result.id)
    if (index >= 0) adminCoupons.value[index] = result
  }
}

async function createSeckillActivity() {
  const wasEditing = editingSeckillActivityId.value !== null
  const payload = {
    ...seckillForm,
    sale_price: Number(seckillForm.sale_price),
    start_time: apiDateTime(seckillForm.start_time),
    end_time: apiDateTime(seckillForm.end_time),
  }
  const result = editingSeckillActivityId.value
    ? await run(() =>
        put<SeckillActivity>(
          `/api/admin/seckill/activities/${editingSeckillActivityId.value}`,
          payload,
          adminToken.value,
        ),
      )
    : await run(() =>
        post<SeckillActivity>(
          '/api/admin/seckill/activities',
          payload,
          adminToken.value,
        ),
      )
  if (!result) return
  const index = adminSeckillActivities.value.findIndex(
    (item) => item.id === result.id,
  )
  if (index >= 0) adminSeckillActivities.value[index] = result
  else adminSeckillActivities.value.unshift(result)
  editingSeckillActivityId.value = null
  seckillForm.name = ''
  seckillForm.sale_price = ''
  seckillForm.start_time = localDateTime(0)
  seckillForm.end_time = localDateTime(1)
  notify(wasEditing ? '秒杀活动已更新' : '秒杀活动已创建', true)
}

function editSeckillActivity(activity: SeckillActivity) {
  editingSeckillActivityId.value = activity.id
  Object.assign(seckillForm, {
    name: activity.name,
    dish_id: activity.dish_id,
    sale_price: activity.sale_price,
    stock: activity.stock,
    limit_per_user: activity.limit_per_user,
    start_time: inputDateTime(activity.start_time),
    end_time: inputDateTime(activity.end_time),
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function cancelSeckillEdit() {
  editingSeckillActivityId.value = null
  Object.assign(seckillForm, {
    name: '',
    dish_id: dishes.value[0]?.id ?? 0,
    sale_price: '',
    stock: 1,
    limit_per_user: 1,
    start_time: localDateTime(0),
    end_time: localDateTime(1),
  })
}

async function toggleSeckillActivity(activity: SeckillActivity) {
  const result = await run(() =>
    patch<SeckillActivity>(
      `/api/admin/seckill/activities/${activity.id}/active`,
      { is_active: !activity.is_active },
      adminToken.value,
    ),
  )
  if (result) {
    const index = adminSeckillActivities.value.findIndex(
      (item) => item.id === result.id,
    )
    if (index >= 0) adminSeckillActivities.value[index] = result
    await run(loadPublicData)
  }
}

async function payOrder(order: Order) {
  const updated = await run(() =>
    post<Order>(`/api/orders/${order.id}/pay`, undefined, userToken.value),
  )
  if (!updated) return
  replaceOrder(orders.value, updated)
  notify('支付成功，商家将尽快接单', true)
}

async function cancelOrder(order: Order) {
  const updated = await run(() =>
    post<Order>(`/api/orders/${order.id}/cancel`, undefined, userToken.value),
  )
  if (updated) replaceOrder(orders.value, updated)
}

async function confirmReceipt(order: Order) {
  const updated = await run(() =>
    post<Order>(
      `/api/orders/${order.id}/confirm-receipt`,
      undefined,
      userToken.value,
    ),
  )
  if (updated) replaceOrder(orders.value, updated)
}

function replaceOrder(list: Order[], updated: Order) {
  const index = list.findIndex((item) => item.id === updated.id)
  if (index >= 0) list[index] = updated
}

async function changeOrderStatus(order: Order, status: OrderStatus) {
  const updated = await run(() =>
    patch<Order>(
      `/api/admin/orders/${order.id}/status`,
      { status },
      adminToken.value,
    ),
  )
  if (updated) replaceOrder(adminOrders.value, updated)
}

function resetDishForm() {
  editingDishId.value = null
  Object.assign(dishForm, {
    name: '',
    image_url: '',
    price: '',
    stock: 0,
    description: '',
    category_id: categories.value[0]?.id ?? 0,
  })
}

function editDish(dish: Dish) {
  editingDishId.value = dish.id
  Object.assign(dishForm, {
    name: dish.name,
    image_url: dish.image_url ?? '',
    price: dish.price,
    stock: dish.stock,
    description: dish.description ?? '',
    category_id: dish.category_id,
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function saveDish() {
  const payload = {
    ...dishForm,
    image_url: dishForm.image_url || null,
    description: dishForm.description || null,
  }
  const result = editingDishId.value
    ? await run(() =>
        put<Dish>(`/api/admin/dishes/${editingDishId.value}`, payload, adminToken.value),
      )
    : await run(() => post<Dish>('/api/admin/dishes', payload, adminToken.value))
  if (!result) return
  const index = dishes.value.findIndex((dish) => dish.id === result.id)
  if (index >= 0) dishes.value[index] = result
  else dishes.value.unshift(result)
  resetDishForm()
  notify('商品信息已保存', true)
}

async function toggleAvailability(dish: Dish) {
  const result = await run(() =>
    patch<Dish>(
      `/api/admin/dishes/${dish.id}/availability`,
      { is_available: !dish.is_available },
      adminToken.value,
    ),
  )
  if (result) {
    const index = dishes.value.findIndex((item) => item.id === dish.id)
    if (index >= 0) dishes.value[index] = result
  }
}

async function deleteDish(dish: Dish) {
  if (!window.confirm(`确定删除「${dish.name}」吗？`)) return
  const result = await run(() =>
    remove(`/api/admin/dishes/${dish.id}`, adminToken.value),
  )
  if (result === null) return
  dishes.value = dishes.value.filter((item) => item.id !== dish.id)
  if (editingDishId.value === dish.id) resetDishForm()
}

async function addCategory() {
  const result = await run(() =>
    post<Category>(
      '/api/categories',
      { name: categoryName.value.trim(), sort_order: categories.value.length },
      adminToken.value,
    ),
  )
  if (!result) return
  categories.value.push(result)
  categoryName.value = ''
  resetDishForm()
  notify('商品分类已创建', true)
}

async function deleteCategory(category: Category) {
  if (!window.confirm(`确定删除「${category.name}」分类吗？`)) return
  const result = await run(() =>
    remove(`/api/categories/${category.id}`, adminToken.value),
  )
  if (result === null) return
  categories.value = categories.value.filter((item) => item.id !== category.id)
  dishes.value = dishes.value.filter((dish) => dish.category_id !== category.id)
  if (activeCategory.value === category.id) activeCategory.value = null
  resetDishForm()
}

async function saveShop() {
  if (!shop.value) return
  const updated = await run(() =>
    put<Shop>(
      '/api/shop',
      {
        shop_name: shop.value?.shop_name,
        description: shop.value?.description,
        business_hours: shop.value?.business_hours,
        delivery_range: shop.value?.delivery_range,
        minimum_order_amount: shop.value?.minimum_order_amount,
        delivery_fee: shop.value?.delivery_fee,
        is_open: shop.value?.is_open,
      },
      adminToken.value,
    ),
  )
  if (updated) {
    shop.value = updated
    notify('店铺信息已更新', true)
  }
}

async function selectView(view: View) {
  activeView.value = view
  if (view === 'orders' && loggedIn.value) await loadUserData()
  if (view === 'merchant') {
    if (!merchantLoggedIn.value) openAuth('admin')
    else await loadMerchantData()
  }
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function formatPrice(price: string | number) {
  return `¥${Number(price).toFixed(2)}`
}

function statusLabel(status: OrderStatus) {
  const labels: Record<OrderStatus, string> = {
    pending_payment: '待支付',
    pending_acceptance: '待接单',
    pending_delivery: '配送中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[status]
}

onMounted(async () => {
  await run(loadPublicData)
  if (errorMessage.value) return
  if (loggedIn.value) await loadUserData()
  if (merchantLoggedIn.value && activeView.value === 'merchant') {
    await loadMerchantData()
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="#" @click.prevent="selectView('discover')">
        <span class="brand-mark">邻</span>
        <span>邻享生活<small>NEIGHBOR SHARE</small></span>
      </a>
      <nav class="main-nav" aria-label="主导航">
        <button :class="{ active: activeView === 'discover' }" @click="selectView('discover')">
          逛一逛
        </button>
        <button :class="{ active: activeView === 'orders' }" @click="selectView('orders')">
          我的订单
        </button>
        <button :class="{ active: activeView === 'merchant' }" @click="selectView('merchant')">
          商家工作台
        </button>
      </nav>
      <div class="account-area">
        <template v-if="loggedIn">
          <span class="account-name">你好，{{ user?.phone }}</span>
          <button class="text-button" @click="logout('user')">退出</button>
        </template>
        <template v-else>
          <button class="text-button" @click="openAuth('user')">登录</button>
          <button class="button button-dark button-small" @click="openAuth('user', 'register')">
            注册
          </button>
        </template>
      </div>
    </header>

    <main>
      <template v-if="activeView === 'discover'">
        <section class="hero">
          <div class="hero-copy">
            <span class="eyebrow"><span class="live-dot"></span> 把附近的好生活带回家</span>
            <h1>邻里好味道，<br />一餐就知道。</h1>
            <p>精选邻享店铺人气好物，新鲜现做，送到你身边。</p>
            <button class="button button-dark" @click="scrollTo('menu')">
              现在去挑选 <span aria-hidden="true">↓</span>
            </button>
            <div class="hero-perks">
              <span>✳ 用心制作</span><span>⌂ 邻里配送</span><span>♡ 温暖日常</span>
            </div>
          </div>
          <div class="hero-art">
            <div class="hero-orbit orbit-one"></div>
            <div class="hero-orbit orbit-two"></div>
            <span class="hero-sun"></span>
            <div class="food-bowl">🍲</div>
            <div class="floating-note note-top">今日好味道 <b>✦</b></div>
            <div class="floating-note note-bottom">新鲜现做 · 暖心送达</div>
            <span class="art-leaf leaf-one">✿</span>
            <span class="art-leaf leaf-two">✧</span>
          </div>
        </section>

        <section v-if="shop" class="shop-strip">
          <div class="shop-identity">
            <span class="shop-avatar">邻</span>
            <span><strong>{{ shop.shop_name }}</strong><small>{{ shop.description || '认真做好每一餐' }}</small></span>
          </div>
          <div class="shop-meta">
            <span><i class="status-dot" :class="{ closed: !shop.is_open }"></i>{{ shop.is_open ? '营业中' : '休息中' }}</span>
            <span>营业 {{ shop.business_hours }}</span>
            <span>配送费 {{ formatPrice(shop.delivery_fee) }}</span>
            <span>起送 {{ formatPrice(shop.minimum_order_amount) }}</span>
          </div>
        </section>

        <section v-if="coupons.length || seckillActivities.length" class="deals-section">
          <div class="section-heading">
            <div><span class="eyebrow">TODAY'S OFFERS</span><h2>优惠与限时秒杀</h2></div>
          </div>
          <div v-if="coupons.length" class="deal-grid">
            <article v-for="coupon in coupons" :key="coupon.id" class="deal-card coupon-card">
              <span class="deal-tag">优惠券</span>
              <strong>{{ coupon.name }}</strong>
              <b>{{ formatPrice(coupon.discount_amount) }} 立减</b>
              <small>满 {{ formatPrice(coupon.minimum_order_amount) }} 可用 · 剩余 {{ coupon.total_quantity - coupon.claimed_quantity }} 张</small>
              <button class="button button-outline button-small" :disabled="busy" @click="claimCoupon(coupon)">领取</button>
            </article>
          </div>
          <div v-if="seckillActivities.length" class="deal-grid">
            <article v-for="activity in seckillActivities" :key="activity.id" class="deal-card seckill-card">
              <span class="deal-tag">限时秒杀 · {{ activity.status === 'upcoming' ? '即将开始' : '进行中' }}</span>
              <strong>{{ activity.name }} · {{ activity.dish_name }}</strong>
              <div><b>{{ formatPrice(activity.sale_price) }}</b><del>{{ formatPrice(activity.original_price) }}</del></div>
              <small>剩余 {{ activity.remaining_stock }} 份 · 每人限购 {{ activity.limit_per_user }} 份</small>
              <button
                class="button button-dark button-small"
                :disabled="busy || activity.status !== 'active' || !shop?.is_open"
                @click="buySeckill(activity)"
              >{{ activity.status === 'upcoming' ? '尚未开始' : activity.status === 'sold_out' ? '已售罄' : '立即抢购' }}</button>
            </article>
          </div>
        </section>

        <section id="menu" class="menu-section">
          <div class="section-heading">
            <div><span class="eyebrow">MADE WITH CARE</span><h2>今天想吃点什么？</h2></div>
            <span class="menu-count">{{ visibleDishes.length }} 款邻里好味</span>
          </div>
          <div class="category-tabs">
            <button :class="{ selected: activeCategory === null }" @click="activeCategory = null">全部</button>
            <button
              v-for="category in categories"
              :key="category.id"
              :class="{ selected: activeCategory === category.id }"
              @click="activeCategory = category.id"
            >
              {{ category.name }}
            </button>
          </div>

          <div v-if="visibleDishes.length" class="dish-grid">
            <article v-for="(dish, index) in visibleDishes" :key="dish.id" class="dish-card">
              <div class="dish-picture" :class="`tone-${index % 4}`">
                <img v-if="dish.image_url" :src="dish.image_url" :alt="dish.name" loading="lazy" />
                <span v-else class="dish-emoji">{{ ['🍛', '🥗', '🍜', '🥘'][index % 4] }}</span>
                <span v-if="dish.stock <= 5" class="stock-label">仅剩 {{ dish.stock }} 份</span>
              </div>
              <div class="dish-info">
                <span class="dish-category">{{ dish.category.name }}</span>
                <h3>{{ dish.name }}</h3>
                <p>{{ dish.description || '邻享精选，认真制作的日常好味。' }}</p>
                <div class="dish-buy">
                  <span class="price">{{ formatPrice(dish.price) }}</span>
                  <button
                    class="add-button"
                    :disabled="!dish.is_available || dish.stock < 1 || !shop?.is_open"
                    :aria-label="`将${dish.name}加入购物车`"
                    @click="addToCart(dish)"
                  >+</button>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">
            <span>🥣</span><strong>暂时还没有上架商品</strong><p>稍后再来看看吧。</p>
          </div>
        </section>

        <section class="story-banner">
          <span class="story-flower">✿</span>
          <div><span class="eyebrow">GOOD FOOD, GOOD NEIGHBORS</span><h2>用一顿好饭，<br />连接身边的温暖。</h2></div>
          <span class="story-stamp">邻里<br />共享<br /><b>♡</b></span>
        </section>
      </template>

      <section v-else-if="activeView === 'orders'" class="page-section">
        <div class="section-heading"><div><span class="eyebrow">YOUR TABLE</span><h2>我的订单</h2></div></div>
        <template v-if="loggedIn">
          <article v-for="order in orders" :key="order.id" class="order-card">
            <div class="order-topline">
              <span>订单号 {{ order.order_no }}</span><strong :class="`order-${order.status}`">{{ statusLabel(order.status) }}</strong>
            </div>
            <div class="order-summary">
              <div class="order-items">
                <span v-for="item in order.items" :key="item.id">{{ item.dish_name }} <small>× {{ item.quantity }}</small></span>
                <small v-if="order.discount_amount !== '0.00'">优惠抵扣 {{ formatPrice(order.discount_amount) }}</small>
                <small>{{ order.recipient_name }} · {{ order.recipient_phone }} · {{ order.city }}{{ order.district }}{{ order.address_detail }}</small>
              </div>
              <div class="order-total"><strong>{{ formatPrice(order.total_amount) }}</strong>
                <button v-if="order.status === 'pending_payment'" class="button button-dark button-small" :disabled="busy" @click="payOrder(order)">支付订单</button>
                <button v-if="order.status === 'pending_payment'" class="text-button" :disabled="busy" @click="cancelOrder(order)">取消</button>
                <button v-if="order.status === 'pending_delivery'" class="button button-outline button-small" :disabled="busy" @click="confirmReceipt(order)">确认收货</button>
              </div>
            </div>
          </article>
          <div v-if="!orders.length" class="empty-state"><span>🧾</span><strong>还没有订单</strong><p>去逛逛，发现喜欢的味道。</p><button class="button button-dark" @click="selectView('discover')">去逛逛</button></div>
        </template>
        <div v-else class="empty-state"><span>☕</span><strong>登录后查看你的订单</strong><button class="button button-dark" @click="openAuth('user')">立即登录</button></div>
      </section>

      <section v-else class="merchant-section">
        <template v-if="merchantLoggedIn">
          <div class="merchant-heading">
            <div><span class="eyebrow">NEIGHBOR SHARE · MERCHANT</span><h2>早上好，{{ admin?.username }}</h2><p>这里是你的邻享店铺经营工作台。</p></div>
            <button class="text-button" @click="logout('admin')">退出商家账号</button>
          </div>
          <div class="stat-grid" v-if="statistics">
            <article class="stat-card"><span>今日营业额</span><strong>{{ formatPrice(statistics.selected_period.revenue) }}</strong><small>已完成订单金额</small></article>
            <article class="stat-card"><span>今日完成订单</span><strong>{{ statistics.selected_period.order_count }}</strong><small>累计售出 {{ statistics.selected_period.dish_sales_quantity }} 件商品</small></article>
            <article class="stat-card"><span>累计营业额</span><strong>{{ formatPrice(statistics.all_time.revenue) }}</strong><small>店铺经营总览</small></article>
          </div>
          <div class="merchant-columns">
            <section class="panel">
              <div class="panel-heading"><div><span class="eyebrow">STORE PROFILE</span><h3>店铺信息</h3></div><button class="button button-outline button-small" :disabled="busy" @click="saveShop">保存修改</button></div>
              <div v-if="shop" class="form-grid">
                <label class="field field-wide">店铺名称<input v-model="shop.shop_name" maxlength="100" /></label>
                <label class="field">营业时间<input v-model="shop.business_hours" /></label>
                <label class="field">配送范围<input v-model="shop.delivery_range" /></label>
                <label class="field">起送金额<input v-model="shop.minimum_order_amount" type="number" min="0" step="0.01" /></label>
                <label class="field">配送费<input v-model="shop.delivery_fee" type="number" min="0" step="0.01" /></label>
                <label class="field field-wide">店铺介绍<textarea v-model="shop.description" rows="2"></textarea></label>
                <label class="switch-field"><input v-model="shop.is_open" type="checkbox" /> 店铺营业中</label>
              </div>
            </section>
            <section class="panel">
              <div class="panel-heading"><div><span class="eyebrow">MENU CATEGORIES</span><h3>商品分类</h3></div></div>
              <form class="category-create" @submit.prevent="addCategory">
                <label class="field"><span class="sr-only">新分类名称</span><input v-model.trim="categoryName" required maxlength="50" placeholder="例如：暖心主食" /></label>
                <button class="button button-dark button-small" type="submit" :disabled="busy">添加分类</button>
              </form>
              <div v-for="category in categories" :key="category.id" class="category-row">
                <span><strong>{{ category.name }}</strong><small>{{ dishes.filter((dish) => dish.category_id === category.id).length }} 款商品</small></span>
                <button class="text-button danger" @click="deleteCategory(category)">删除</button>
              </div>
            </section>
            <section class="panel">
              <div class="panel-heading"><div><span class="eyebrow">ADD SOMETHING GOOD</span><h3>{{ editingDishId ? '编辑商品' : '新增商品' }}</h3></div><button v-if="editingDishId" class="text-button" @click="resetDishForm">取消编辑</button></div>
              <form class="form-grid" @submit.prevent="saveDish">
                <label class="field">商品名称<input v-model.trim="dishForm.name" required maxlength="100" /></label>
                <label class="field">所属分类<select v-model.number="dishForm.category_id" required><option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option></select></label>
                <label class="field">价格<input v-model="dishForm.price" type="number" min="0" step="0.01" required /></label>
                <label class="field">库存<input v-model.number="dishForm.stock" type="number" min="0" required /></label>
                <label class="field field-wide">图片地址<input v-model.trim="dishForm.image_url" type="url" placeholder="https://..." /></label>
                <label class="field field-wide">商品介绍<textarea v-model.trim="dishForm.description" rows="2"></textarea></label>
                <button class="button button-dark field-wide" type="submit" :disabled="busy || !categories.length">{{ editingDishId ? '保存商品' : '添加商品' }}</button>
              </form>
            </section>
          </div>
          <div class="merchant-columns">
            <section class="panel">
              <div class="panel-heading"><div><span class="eyebrow">COUPON CAMPAIGNS</span><h3>{{ editingCouponId ? '编辑优惠券' : '优惠券管理' }}</h3></div><button v-if="editingCouponId" class="text-button" @click="cancelCouponEdit">取消编辑</button></div>
              <form class="form-grid" @submit.prevent="createCoupon">
                <label class="field field-wide">优惠券名称<input v-model.trim="couponForm.name" required maxlength="100" /></label>
                <label class="field">立减金额<input v-model="couponForm.discount_amount" type="number" min="0.01" step="0.01" :disabled="editingCouponHasClaims" required /></label>
                <label class="field">使用门槛<input v-model="couponForm.minimum_order_amount" type="number" min="0" step="0.01" :disabled="editingCouponHasClaims" required /></label>
                <label class="field">发放数量<input v-model.number="couponForm.total_quantity" type="number" min="1" required /></label>
                <label class="field">每人限领<input v-model.number="couponForm.per_user_limit" type="number" min="1" required /></label>
                <label class="field">开始时间<input v-model="couponForm.start_time" type="datetime-local" :disabled="editingCouponHasClaims" required /></label>
                <label class="field">结束时间<input v-model="couponForm.end_time" type="datetime-local" :disabled="editingCouponHasClaims" required /></label>
                <label class="field field-wide">使用说明<input v-model.trim="couponForm.description" maxlength="500" /></label>
                <button class="button button-dark field-wide" type="submit" :disabled="busy">{{ editingCouponId ? '保存优惠券' : '创建优惠券' }}</button>
              </form>
              <div v-for="coupon in adminCoupons" :key="coupon.id" class="deal-admin-row">
                <span><strong>{{ coupon.name }}</strong><small>{{ formatPrice(coupon.discount_amount) }} 立减 · 已领 {{ coupon.claimed_quantity }}/{{ coupon.total_quantity }}</small></span>
                <div class="merchant-actions"><button class="text-button" :disabled="busy" @click="editCoupon(coupon)">编辑</button><button class="text-button" :disabled="busy" @click="toggleCoupon(coupon)">{{ coupon.is_active ? '停用' : '启用' }}</button></div>
              </div>
              <div v-if="!adminCoupons.length" class="empty-inline">还没有优惠券。</div>
            </section>
            <section class="panel">
              <div class="panel-heading"><div><span class="eyebrow">LIMITED-TIME SALES</span><h3>{{ editingSeckillActivityId ? '编辑秒杀活动' : '秒杀活动' }}</h3></div><button v-if="editingSeckillActivityId" class="text-button" @click="cancelSeckillEdit">取消编辑</button></div>
              <form class="form-grid" @submit.prevent="createSeckillActivity">
                <label class="field field-wide">活动名称<input v-model.trim="seckillForm.name" required maxlength="100" /></label>
                <label class="field field-wide">秒杀商品<select v-model.number="seckillForm.dish_id" :disabled="editingSeckillActivityId !== null" required><option v-for="dish in dishes" :key="dish.id" :value="dish.id">{{ dish.name }} · 原价 {{ formatPrice(dish.price) }}</option></select></label>
                <label class="field">秒杀价<input v-model="seckillForm.sale_price" type="number" min="0" step="0.01" required /></label>
                <label class="field">活动库存<input v-model.number="seckillForm.stock" type="number" min="1" required /></label>
                <label class="field">每人限购<input v-model.number="seckillForm.limit_per_user" type="number" min="1" required /></label>
                <label class="field">开始时间<input v-model="seckillForm.start_time" type="datetime-local" required /></label>
                <label class="field">结束时间<input v-model="seckillForm.end_time" type="datetime-local" required /></label>
                <button class="button button-dark field-wide" type="submit" :disabled="busy || !dishes.length">{{ editingSeckillActivityId ? '保存活动' : '创建活动' }}</button>
              </form>
              <div v-for="activity in adminSeckillActivities" :key="activity.id" class="deal-admin-row">
                <span><strong>{{ activity.name }} · {{ activity.dish_name }}</strong><small>{{ formatPrice(activity.sale_price) }} · 剩余 {{ activity.remaining_stock }}/{{ activity.stock }} · {{ activity.status }}</small></span>
                <div class="merchant-actions"><button class="text-button" :disabled="busy" @click="editSeckillActivity(activity)">编辑</button><button class="text-button" :disabled="busy" @click="toggleSeckillActivity(activity)">{{ activity.is_active ? '停止' : '启用' }}</button></div>
              </div>
              <div v-if="!adminSeckillActivities.length" class="empty-inline">还没有秒杀活动。</div>
            </section>
          </div>
          <section class="panel merchant-list-panel">
            <div class="panel-heading"><div><span class="eyebrow">YOUR MENU</span><h3>商品管理 <small>{{ dishes.length }} 款</small></h3></div></div>
            <div v-for="dish in dishes" :key="dish.id" class="merchant-dish">
              <div class="mini-dish-image"><img v-if="dish.image_url" :src="dish.image_url" :alt="dish.name" /><span v-else>🍱</span></div>
              <div class="merchant-dish-name"><strong>{{ dish.name }}</strong><small>{{ dish.category.name }} · 库存 {{ dish.stock }}</small></div>
              <strong class="price">{{ formatPrice(dish.price) }}</strong>
              <span class="availability" :class="{ unavailable: !dish.is_available }">{{ dish.is_available ? '已上架' : '已下架' }}</span>
              <div class="merchant-actions"><button class="text-button" @click="editDish(dish)">编辑</button><button class="text-button" @click="toggleAvailability(dish)">{{ dish.is_available ? '下架' : '上架' }}</button><button class="text-button danger" @click="deleteDish(dish)">删除</button></div>
            </div>
            <div v-if="!dishes.length" class="empty-inline">还没有商品，添加第一款商品吧。</div>
          </section>
          <section class="panel merchant-list-panel">
            <div class="panel-heading"><div><span class="eyebrow">ORDERS</span><h3>近期订单 <small>{{ adminOrders.length }} 笔</small></h3></div><button class="button button-outline button-small" @click="loadMerchantData">刷新</button></div>
            <div v-for="order in adminOrders" :key="order.id" class="admin-order-row">
              <div><strong>{{ order.recipient_name }} · {{ formatPrice(order.total_amount) }}</strong><small>{{ order.order_no }} · {{ order.items.map((item) => `${item.dish_name} ×${item.quantity}`).join('、') }}</small></div>
              <span class="availability">{{ statusLabel(order.status) }}</span>
              <select v-if="order.status !== 'completed' && order.status !== 'cancelled'" :value="order.status" @change="changeOrderStatus(order, ($event.target as HTMLSelectElement).value as OrderStatus)">
                <option disabled :value="order.status">{{ statusLabel(order.status) }}</option>
                <option v-if="order.status === 'pending_payment'" value="pending_acceptance">确认接单</option>
                <option v-if="order.status === 'pending_acceptance'" value="pending_delivery">开始配送</option>
                <option v-if="order.status === 'pending_acceptance' || order.status === 'pending_delivery'" value="cancelled">取消订单</option>
              </select>
            </div>
            <div v-if="!adminOrders.length" class="empty-inline">还没有订单。</div>
          </section>
          <section class="panel merchant-list-panel">
            <div class="panel-heading"><div><span class="eyebrow">BEST SELLERS</span><h3>热销商品</h3></div></div>
            <div v-for="(item, index) in statistics?.dish_sales_ranking ?? []" :key="`${item.dish_name}-${index}`" class="ranking-row"><span class="rank-number">0{{ index + 1 }}</span><strong>{{ item.dish_name }}</strong><small>{{ item.category_name }}</small><span>售出 {{ item.quantity }}</span><b>{{ formatPrice(item.sales_amount) }}</b></div>
          </section>
        </template>
        <div v-else class="merchant-login">
          <span class="merchant-icon">✳</span><span class="eyebrow">NEIGHBOR SHARE · MERCHANT</span>
          <h2>把好味道，分享给邻里。</h2><p>登录商家工作台，管理店铺、商品与订单。</p>
          <button class="button button-dark" @click="openAuth('admin')">商家登录</button>
          <button class="text-button" @click="openAuth('admin', 'register')">还没有商家账号？立即注册</button>
        </div>
      </section>
    </main>

    <aside v-if="activeView === 'discover'" class="cart-dock">
      <button class="cart-dock-main" @click="scrollTo('cart-panel')">
        <span class="cart-icon">🛍</span><span>我的购物袋 <small>{{ cartItemsCount }} 件商品</small></span><b>{{ formatPrice(cart.total_amount) }}</b>
      </button>
    </aside>

    <section v-if="activeView === 'discover' && cart.items.length" id="cart-panel" class="cart-panel">
      <div class="cart-heading"><div><span class="eyebrow">YOUR BAG</span><h3>购物袋 <small>{{ cart.total_quantity }} 件</small></h3></div><button class="text-button" @click="loadCart">刷新</button></div>
      <div v-for="item in cart.items" :key="item.dish_id" class="cart-line">
        <span class="cart-thumb">🍱</span><span class="cart-dish"><strong>{{ item.dish.name }}</strong><small>{{ formatPrice(item.dish.price) }}</small></span>
        <div class="quantity-control"><button :aria-label="`减少${item.dish.name}数量`" @click="setQuantity(item.dish_id, item.quantity - 1)">−</button><span>{{ item.quantity }}</span><button :aria-label="`增加${item.dish.name}数量`" @click="setQuantity(item.dish_id, item.quantity + 1)">+</button></div>
      </div>
      <div class="address-choice">
        <div class="cart-heading"><strong>收货地址</strong><button class="text-button" @click="openAddressDialog">＋ 新增</button></div>
        <template v-if="addresses.length">
          <select v-model.number="selectedAddressId">
            <option v-for="address in addresses" :key="address.id" :value="address.id">{{ address.recipient_name }} · {{ address.phone }} · {{ address.city }}{{ address.district }}{{ address.detail }}</option>
          </select>
          <div v-if="activeAddress" class="address-actions">
            <span v-if="activeAddress.is_default" class="default-address-label">默认地址</span>
            <button v-else class="text-button" @click="setDefaultAddress(activeAddress)">设为默认</button>
            <button class="text-button" @click="editAddress(activeAddress)">编辑</button>
            <button class="text-button danger" @click="deleteAddress(activeAddress)">删除</button>
          </div>
        </template>
        <button v-else class="address-empty" @click="openAddressDialog">＋ 添加收货地址</button>
      </div>
      <div class="cart-total"><span>商品金额 <small>配送费以结算为准</small></span><strong>{{ formatPrice(cart.total_amount) }}</strong></div>
      <div v-if="availableUserCoupons.length" class="coupon-choice">
        <label class="field">使用优惠券
          <select v-model.number="selectedUserCouponId">
            <option :value="null">不使用优惠券</option>
            <option v-for="userCoupon in availableUserCoupons" :key="userCoupon.id" :value="userCoupon.id">
              {{ userCoupon.coupon.name }} · 立减 {{ formatPrice(userCoupon.coupon.discount_amount) }}
            </option>
          </select>
        </label>
        <small v-if="selectedUserCoupon && couponDiscountPreview === 0">商品金额未达到使用门槛 {{ formatPrice(selectedUserCoupon.coupon.minimum_order_amount) }}</small>
        <small v-else-if="couponDiscountPreview > 0">优惠 {{ formatPrice(couponDiscountPreview) }}</small>
      </div>
      <button class="button button-dark checkout-button" :disabled="busy || !shop?.is_open || !cart.items.length" @click="checkout">去结算 <span>{{ formatPrice(checkoutTotalPreview) }}</span></button>
    </section>

    <footer class="footer"><span>邻享生活 <small>把邻里的美好，分享给每一天。</small></span><span>邻里好味 · 用心分享</span></footer>

    <div v-if="errorMessage || successMessage" class="toast" :class="{ 'toast-success': successMessage }" role="status">
      <span>{{ successMessage || errorMessage }}</span><button @click="errorMessage = ''; successMessage = ''">×</button>
    </div>

    <div v-if="authDialog" class="modal-backdrop" @click.self="authDialog = false">
      <section class="modal">
        <button class="modal-close" aria-label="关闭" @click="authDialog = false">×</button>
        <span class="eyebrow">{{ authRole === 'user' ? 'WELCOME TO THE NEIGHBORHOOD' : 'MERCHANT ACCESS' }}</span>
        <h2>{{ authRole === 'user' ? '邻享一餐好时光。' : '欢迎回到店铺。' }}</h2>
        <div class="role-tabs"><button :class="{ selected: authRole === 'user' }" @click="authRole = 'user'">消费者</button><button :class="{ selected: authRole === 'admin' }" @click="authRole = 'admin'">商家</button></div>
        <form class="modal-form" @submit.prevent="submitAuth">
          <label v-if="authRole === 'user'" class="field">手机号<input v-model.trim="authForm.phone" type="tel" autocomplete="tel" placeholder="请输入手机号" pattern="1[3-9][0-9]{9}" required /></label>
          <label v-else class="field">商家账号<input v-model.trim="authForm.username" autocomplete="username" placeholder="请输入商家账号" minlength="3" maxlength="50" required /></label>
          <label class="field">密码<input v-model="authForm.password" type="password" autocomplete="current-password" placeholder="至少 8 位" minlength="8" maxlength="72" required /></label>
          <button class="button button-dark modal-submit" :disabled="busy">{{ authMode === 'login' ? '登录' : '创建账号' }}</button>
        </form>
        <button class="text-button auth-switch" @click="authMode = authMode === 'login' ? 'register' : 'login'">
          {{ authMode === 'login' ? '还没有账号？现在注册' : '已有账号？返回登录' }}
        </button>
      </section>
    </div>

    <div v-if="addressDialog" class="modal-backdrop" @click.self="addressDialog = false">
      <section class="modal">
        <button class="modal-close" aria-label="关闭" @click="addressDialog = false">×</button>
        <span class="eyebrow">DELIVERY DETAILS</span><h2>{{ editingAddressId ? '编辑收货地址' : '送到哪里？' }}</h2>
        <form class="modal-form" @submit.prevent="addAddress">
          <div class="form-grid">
            <label class="field">收件人<input v-model.trim="addressForm.recipient_name" required maxlength="50" /></label>
            <label class="field">手机号<input v-model.trim="addressForm.phone" type="tel" pattern="1[3-9][0-9]{9}" required /></label>
            <label class="field">省份<input v-model.trim="addressForm.province" required maxlength="50" /></label>
            <label class="field">城市<input v-model.trim="addressForm.city" required maxlength="50" /></label>
            <label class="field">区/县<input v-model.trim="addressForm.district" required maxlength="50" /></label>
            <label class="field field-wide">详细地址<input v-model.trim="addressForm.detail" required maxlength="255" /></label>
          </div>
          <button class="button button-dark modal-submit" :disabled="busy">保存地址</button>
        </form>
      </section>
    </div>
  </div>
</template>

<style>
@import './style.css';
</style>
