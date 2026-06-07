import http, { type CommonResult } from './http'

export interface OverviewPeriod {
  order_count: number
  gmv: number
  gmvChangePct?: number | null
  orderChangePct?: number | null
}

export interface DashboardOverview {
  refDate: string
  today: OverviewPeriod
  week: OverviewPeriod
  month: OverviewPeriod
}

export async function fetchOverview(refDate?: string) {
  const res = (await http.get('/ops/dashboard/overview', { params: { refDate } })) as CommonResult<DashboardOverview>
  return res.data
}

export async function fetchOrderHourly(refDate?: string) {
  const res = (await http.get('/ops/dashboard/order-hourly', { params: { refDate } })) as CommonResult<
    Array<{ stat_hour: number; order_count: number; gmv: number }>
  >
  return res.data
}

export async function fetchFunnel(refDate?: string) {
  const res = (await http.get('/ops/dashboard/funnel', { params: { refDate } })) as CommonResult<{
    refDate: string
    stages: Array<{ name: string; value: number }>
  }>
  return res.data
}

export async function fetchMemberActive(refDate?: string, days = 14) {
  const res = (await http.get('/ops/dashboard/member-active', { params: { refDate, days } })) as CommonResult<{
    refDate: string
    trend: Array<{ stat_date: string; uv: number; pv: number; active_member_count: number }>
    latest: { uv: number; pv: number; active_member_count: number }
  }>
  return res.data
}

export async function fetchRegionSales(refDate?: string, limit = 10) {
  const res = (await http.get('/ops/dashboard/region-sales', { params: { refDate, limit } })) as CommonResult<{
    refDate: string
    regions: Array<{ province: string; order_count: number; gmv: number }>
  }>
  return res.data
}

export async function fetchOrderTrend(refDate?: string, days = 30) {
  const res = (await http.get('/ops/dashboard/order-trend', { params: { refDate, days } })) as CommonResult<{
    refDate: string
    trend: Array<{ stat_date: string; order_count: number; gmv: number }>
  }>
  return res.data
}

export async function fetchProductTop(refDate?: string, limit = 10) {
  const res = (await http.get('/ops/dashboard/product-top', { params: { refDate, limit } })) as CommonResult<{
    refDate: string
    products: Array<{ rank_num?: number; product_id: number; product_name: string; order_count: number; gmv: number }>
  }>
  return res.data
}

export async function fetchOrderStatus(refDate?: string) {
  const res = (await http.get('/ops/dashboard/order-status', { params: { refDate } })) as CommonResult<{
    refDate: string
    statuses: Array<{ status: number; status_name: string; order_count: number }>
  }>
  return res.data
}

export async function fetchAdsMeta() {
  const res = (await http.get('/ops/ads/meta')) as CommonResult<{
    tables: Record<string, { cnt: number; updated_at?: string }>
    dateRange: { min_date?: string; max_date?: string }
  }>
  return res.data
}

export async function refreshAds() {
  const res = (await http.post('/ops/ads/refresh')) as CommonResult<{ refreshed: Record<string, number> }>
  return res.data
}
