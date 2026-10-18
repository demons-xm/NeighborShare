export interface ApiResponse<T> {
  code: number
  message: string
  data: T | null
}

export interface User {
  id: number
  phone: string
  create_time: string
}

export interface Admin {
  id: number
  username: string
  create_time: string
}

export interface LoginData<T> {
  access_token: string
  token_type: string
  expires_in: number
  user?: T
  admin?: T
}

export interface Shop {
  id: number
  shop_name: string
  logo_url: string | null
  description: string
  business_hours: string
  delivery_range: string
  minimum_order_amount: string
  delivery_fee: string
  is_open: boolean
}

export interface Category {
  id: number
  name: string
  description: string | null
  sort_order: number
}

export interface Dish {
  id: number
  name: string
  image_url: string | null
  price: string
  stock: number
  description: string | null
  category_id: number
  is_available: boolean
  category: Category
}

export interface Address {
  id: number
  recipient_name: string
  phone: string
  province: string
  city: string
  district: string
  detail: string
  is_default: boolean
}

export interface CartItem {
  dish_id: number
  quantity: number
  dish: Dish
}

export interface Cart {
  items: CartItem[]
  total_quantity: number
  total_amount: string
}

export interface OrderItem {
  id: number
  dish_id: number | null
  dish_name: string
  dish_image_url: string | null
  category_name: string
  unit_price: string
  quantity: number
  subtotal: string
}

export type OrderStatus =
  | 'pending_payment'
  | 'pending_acceptance'
  | 'pending_delivery'
  | 'completed'
  | 'cancelled'

export interface Order {
  id: number
  order_no: string
  status: OrderStatus
  recipient_name: string
  recipient_phone: string
  province: string
  city: string
  district: string
  address_detail: string
  dish_amount: string
  delivery_fee: string
  total_amount: string
  create_time: string
  items: OrderItem[]
}

export interface Statistics {
  period: string
  start_date: string
  end_date: string
  all_time: StatisticsTotals
  selected_period: StatisticsTotals
  dish_sales_ranking: Array<{
    dish_name: string
    category_name: string
    quantity: number
    sales_amount: string
  }>
}

export interface StatisticsTotals {
  order_count: number
  revenue: string
  dish_revenue: string
  delivery_revenue: string
  dish_sales_quantity: number
}
