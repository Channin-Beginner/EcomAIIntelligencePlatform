import http, { type CommonResult } from './http'

export interface Product {
  id: number
  name: string
  pic?: string
  price?: number
  sub_title?: string
  sale?: number
  stock?: number
  brand_name?: string
  product_category_name?: string
}

export interface PageResult<T> {
  list: T[]
  total: number
  pageNum: number
  pageSize: number
  totalPage: number
}

export interface HomeCategory {
  id: number
  name: string
  product_count?: number
}

export interface Brand {
  id: number
  name: string
  logo?: string
}

export interface HomeContent {
  advertiseList?: { id: number; name: string; pic?: string; url?: string }[]
  brandList?: Brand[]
  hotProductList?: Product[]
  newProductList?: Product[]
  categoryNavList?: HomeCategory[]
  totalProductCount?: number
}

export function fetchHomeContent() {
  return http.get<unknown, CommonResult<HomeContent>>('/home/content')
}

export function fetchProductFeed(params: {
  tab?: 'all' | 'hot' | 'new' | 'recommend'
  categoryId?: number
  pageNum?: number
  pageSize?: number
}) {
  return http.get<unknown, CommonResult<PageResult<Product>>>('/home/productFeed', { params })
}

export function fetchProductDetail(id: number) {
  return http.get<unknown, CommonResult>(`/product/detail/${id}`)
}

export function searchProducts(keyword: string, pageNum = 1, pageSize = 12) {
  return http.get<unknown, CommonResult>('/product/search', { params: { keyword, pageNum, pageSize } })
}

export function login(username: string, password: string) {
  return http.post<unknown, CommonResult>('/sso/login', { username, password })
}

export function register(data: {
  username: string
  password: string
  nickname?: string
  telephone?: string
}) {
  return http.post<unknown, CommonResult>('/sso/register', data)
}

export function fetchMemberInfo() {
  return http.get<unknown, CommonResult>('/sso/info')
}

export function fetchCartList() {
  return http.get<unknown, CommonResult>('/cart/list')
}

export function addToCart(productId: number, productSkuId?: number, quantity = 1) {
  return http.post<unknown, CommonResult>('/cart/add', { productId, productSkuId, quantity })
}

export function updateCartQuantity(id: number, quantity: number) {
  return http.get<unknown, CommonResult>('/cart/update/quantity', { params: { id, quantity } })
}

export function deleteCartItems(ids: number[]) {
  return http.post<unknown, CommonResult>('/cart/delete', null, { params: { ids } })
}

export function fetchAddressList() {
  return http.get<unknown, CommonResult>('/member/address/list')
}

export function addAddress(data: Record<string, unknown>) {
  return http.post<unknown, CommonResult>('/member/address/add', data)
}

export function confirmOrder(cartIds: number[]) {
  return http.post<unknown, CommonResult>('/order/generateConfirmOrder', cartIds)
}

export function createOrder(data: {
  memberReceiveAddressId: number
  payType: number
  cartIds: number[]
}) {
  return http.post<unknown, CommonResult>('/order/generateOrder', data)
}

export function payOrder(orderId: number, payType = 1) {
  return http.post<unknown, CommonResult>('/order/paySuccess', null, { params: { orderId, payType } })
}

export function fetchOrders(status = -1, pageNum = 1, pageSize = 10) {
  return http.get<unknown, CommonResult>('/order/list', { params: { status, pageNum, pageSize } })
}

export function fetchBrandProducts(brandId: number, pageNum = 1) {
  return http.get<unknown, CommonResult>('/brand/productList', { params: { brandId, pageNum } })
}

export interface ForYouFeedResult extends PageResult<Product> {
  strategy?: string
  modelReady?: boolean
}

export function fetchForYouFeed(pageNum = 1, pageSize = 20) {
  return http.get<unknown, CommonResult<ForYouFeedResult>>('/recommend/forYou', {
    params: { pageNum, pageSize },
  })
}

export function fetchSimilarProducts(productId: number, pageSize = 10) {
  return http.get<unknown, CommonResult<{ list: Product[] }>>(
    `/recommend/similar/${productId}`,
    { params: { pageSize } },
  )
}

export interface CollectionItem {
  id: number
  productId: number
  product: Product
}

export function fetchCollectionList() {
  return http.get<unknown, CommonResult<CollectionItem[]>>('/member/collection/list')
}

export function fetchCollectionStatus(productId: number) {
  return http.get<unknown, CommonResult<{ collected: boolean }>>('/member/collection/status', {
    params: { productId },
  })
}

export function addCollection(productId: number) {
  return http.post<unknown, CommonResult>('/member/collection/add', { productId })
}

export function removeCollection(productId: number) {
  return http.post<unknown, CommonResult>('/member/collection/delete', null, {
    params: { productId },
  })
}
