<script setup lang="ts">
import { computed, onMounted, provide, ref } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, FunnelChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { todayYmd } from '@/utils/date'
import {
  fetchFunnel,
  fetchMemberActive,
  fetchOrderHourly,
  fetchOrderStatus,
  fetchOrderTrend,
  fetchOverview,
  fetchProductTop,
  fetchRegionSales,
  refreshAds,
  type DashboardOverview,
} from '@/api/ops'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  FunnelChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const refDate = ref(todayYmd())
provide('opsRefDate', refDate)
const loading = ref(false)
const errorMsg = ref('')
const overview = ref<DashboardOverview | null>(null)
const hourly = ref<Array<{ stat_hour: number; order_count: number; gmv: number }>>([])
const funnelStages = ref<Array<{ name: string; value: number }>>([])
const memberTrend = ref<Array<{ stat_date: string; uv: number; pv: number }>>([])
const memberLatest = ref({ uv: 0, pv: 0, active_member_count: 0 })
const regions = ref<Array<{ province: string; order_count: number; gmv: number }>>([])
const orderTrend = ref<Array<{ stat_date: string; order_count: number; gmv: number }>>([])
const products = ref<Array<{ product_name: string; gmv: number; order_count: number }>>([])
const orderStatuses = ref<Array<{ status_name: string; order_count: number }>>([])

const formatMoney = (v: number) =>
  v >= 10000 ? `¥${(v / 10000).toFixed(2)}万` : `¥${v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`

const formatPct = (v?: number | null) => {
  if (v == null) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}%`
}

const hourlyOption = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const map = new Map(hourly.value.map(h => [h.stat_hour, h]))
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: hours, axisLabel: { color: '#7da4c7', fontSize: 10 } },
    yAxis: [
      { type: 'value', name: 'GMV', axisLabel: { color: '#7da4c7' }, splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)' } } },
      { type: 'value', name: '订单', axisLabel: { color: '#7da4c7' }, splitLine: { show: false } },
    ],
    series: [
      {
        name: 'GMV',
        type: 'line',
        smooth: true,
        areaStyle: { color: 'rgba(56,189,248,0.15)' },
        itemStyle: { color: '#38bdf8' },
        data: hours.map((_, i) => map.get(i)?.gmv ?? 0),
      },
      {
        name: '订单数',
        type: 'bar',
        yAxisIndex: 1,
        itemStyle: { color: 'rgba(52,211,153,0.75)' },
        data: hours.map((_, i) => map.get(i)?.order_count ?? 0),
      },
    ],
  }
})

const funnelOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}' },
  series: [
    {
      type: 'funnel',
      left: '8%',
      width: '84%',
      sort: 'descending',
      gap: 4,
      label: { color: '#e8f4ff' },
      itemStyle: { borderColor: '#050b18' },
      data: funnelStages.value,
    },
  ],
}))

const memberOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['UV', 'PV'], textStyle: { color: '#7da4c7' }, top: 0 },
  grid: { left: 48, right: 24, top: 36, bottom: 28 },
  xAxis: {
    type: 'category',
    data: memberTrend.value.map(d => d.stat_date.slice(5)),
    axisLabel: { color: '#7da4c7', fontSize: 10 },
  },
  yAxis: { type: 'value', axisLabel: { color: '#7da4c7' }, splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)' } } },
  series: [
    { name: 'UV', type: 'line', smooth: true, data: memberTrend.value.map(d => d.uv), itemStyle: { color: '#38bdf8' } },
    { name: 'PV', type: 'line', smooth: true, data: memberTrend.value.map(d => d.pv), itemStyle: { color: '#fbbf24' } },
  ],
}))

const regionOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 72, right: 24, top: 16, bottom: 24 },
  xAxis: { type: 'value', axisLabel: { color: '#7da4c7' }, splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)' } } },
  yAxis: {
    type: 'category',
    data: [...regions.value].reverse().map(r => r.province),
    axisLabel: { color: '#7da4c7', fontSize: 11 },
  },
  series: [
    {
      type: 'bar',
      data: [...regions.value].reverse().map(r => r.gmv),
      itemStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: '#0ea5e9' },
            { offset: 1, color: '#34d399' },
          ],
        },
      },
      label: { show: true, position: 'right', color: '#7da4c7', formatter: (p: { value: number }) => formatMoney(p.value) },
    },
  ],
}))

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['订单数', 'GMV'], textStyle: { color: '#7da4c7' }, top: 0 },
  grid: { left: 48, right: 48, top: 36, bottom: 28 },
  xAxis: {
    type: 'category',
    data: orderTrend.value.map(d => d.stat_date.slice(5)),
    axisLabel: { color: '#7da4c7', fontSize: 10 },
  },
  yAxis: [
    { type: 'value', name: '订单', axisLabel: { color: '#7da4c7' }, splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)' } } },
    { type: 'value', name: 'GMV', axisLabel: { color: '#7da4c7' }, splitLine: { show: false } },
  ],
  series: [
    { name: '订单数', type: 'bar', data: orderTrend.value.map(d => d.order_count), itemStyle: { color: 'rgba(56,189,248,0.7)' } },
    { name: 'GMV', type: 'line', yAxisIndex: 1, smooth: true, data: orderTrend.value.map(d => d.gmv), itemStyle: { color: '#34d399' } },
  ],
}))

const productOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 24, top: 16, bottom: 56 },
  xAxis: {
    type: 'category',
    data: products.value.map(p => (p.product_name || '').slice(0, 8)),
    axisLabel: { color: '#7da4c7', rotate: 30, fontSize: 10 },
  },
  yAxis: { type: 'value', axisLabel: { color: '#7da4c7' }, splitLine: { lineStyle: { color: 'rgba(56,189,248,0.08)' } } },
  series: [
    {
      type: 'bar',
      data: products.value.map(p => p.gmv),
      itemStyle: { color: '#fbbf24' },
    },
  ],
}))

const statusOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 8, top: 'center', textStyle: { color: '#7da4c7', fontSize: 11 } },
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['38%', '50%'],
      label: { color: '#e8f4ff', fontSize: 11 },
      data: orderStatuses.value.map(s => ({ name: s.status_name, value: s.order_count })),
      itemStyle: {
        borderColor: '#050b18',
        borderWidth: 2,
      },
    },
  ],
}))

async function loadDashboard() {
  loading.value = true
  errorMsg.value = ''
  try {
    const date = refDate.value
    const [ov, hr, fn, ma, rg, tr, pt, st] = await Promise.all([
      fetchOverview(date),
      fetchOrderHourly(date),
      fetchFunnel(date),
      fetchMemberActive(date, 14),
      fetchRegionSales(date, 10),
      fetchOrderTrend(date, 30),
      fetchProductTop(date, 10),
      fetchOrderStatus(date),
    ])
    overview.value = ov
    hourly.value = hr
    funnelStages.value = fn.stages
    memberTrend.value = ma.trend
    memberLatest.value = ma.latest
    regions.value = rg.regions
    orderTrend.value = tr.trend
    products.value = pt.products
    orderStatuses.value = st.statuses
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleRefreshAds() {
  loading.value = true
  try {
    await refreshAds()
    await loadDashboard()
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : 'ADS 刷新失败'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  refDate.value = todayYmd()
  await loadDashboard()
})
</script>

<template>
  <div class="ops-screen">
    <header class="ops-header">
      <div class="ops-header__left">
        <span class="ops-badge">Phase 5 · BI</span>
        <h1>EcomAI 电商运营智脑大屏</h1>
      </div>
      <div class="ops-header__center">
        <label>
          参考日期
          <input v-model="refDate" type="date" @change="loadDashboard" />
        </label>
        <button class="btn" :disabled="loading" @click="loadDashboard">刷新数据</button>
        <button class="btn btn--ghost" :disabled="loading" @click="handleRefreshAds">刷新 ADS</button>
      </div>
      <div class="ops-header__right">
        <span v-if="errorMsg" class="ops-error">{{ errorMsg }}</span>
      </div>
    </header>

    <section v-if="overview" class="kpi-row">
      <article class="kpi-card">
        <div class="kpi-card__label">当日订单</div>
        <div class="kpi-card__value">{{ overview.today.order_count }}</div>
        <div class="kpi-card__sub" :class="{ up: (overview.today.orderChangePct ?? 0) > 0, down: (overview.today.orderChangePct ?? 0) < 0 }">
          环比 {{ formatPct(overview.today.orderChangePct) }}
        </div>
      </article>
      <article class="kpi-card">
        <div class="kpi-card__label">当日 GMV</div>
        <div class="kpi-card__value">{{ formatMoney(overview.today.gmv) }}</div>
        <div class="kpi-card__sub" :class="{ up: (overview.today.gmvChangePct ?? 0) > 0, down: (overview.today.gmvChangePct ?? 0) < 0 }">
          环比 {{ formatPct(overview.today.gmvChangePct) }}
        </div>
      </article>
      <article class="kpi-card">
        <div class="kpi-card__label">本周订单 / GMV</div>
        <div class="kpi-card__value">{{ overview.week.order_count }} / {{ formatMoney(overview.week.gmv) }}</div>
        <div class="kpi-card__sub">周环比订单 {{ formatPct(overview.week.orderChangePct) }}</div>
      </article>
      <article class="kpi-card">
        <div class="kpi-card__label">本月订单 / GMV</div>
        <div class="kpi-card__value">{{ overview.month.order_count }} / {{ formatMoney(overview.month.gmv) }}</div>
        <div class="kpi-card__sub">月环比 GMV {{ formatPct(overview.month.gmvChangePct) }}</div>
      </article>
      <article class="kpi-card kpi-card--accent">
        <div class="kpi-card__label">当日 UV / PV</div>
        <div class="kpi-card__value">{{ memberLatest.uv }} / {{ memberLatest.pv }}</div>
        <div class="kpi-card__sub">活跃会员 {{ memberLatest.active_member_count }}</div>
      </article>
    </section>

    <section class="grid-2x2">
      <article class="panel">
        <h2 class="panel__title">① 24 小时销售曲线</h2>
        <div class="panel__chart">
          <v-chart v-if="!loading" :option="hourlyOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel">
        <h2 class="panel__title">② 转化漏斗</h2>
        <div class="panel__chart">
          <v-chart v-if="!loading" :option="funnelOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel">
        <h2 class="panel__title">③ UV / PV 活跃趋势（14 日）</h2>
        <div class="panel__chart">
          <v-chart v-if="!loading" :option="memberOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel">
        <h2 class="panel__title">④ 地域销售 TOP10</h2>
        <div class="panel__chart">
          <v-chart v-if="!loading" :option="regionOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel panel--wide">
        <h2 class="panel__title">⑤ 近 30 日订单趋势</h2>
        <div class="panel__chart panel__chart--tall">
          <v-chart v-if="!loading" :option="trendOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel">
        <h2 class="panel__title">⑥ 热销商品 TOP10</h2>
        <div class="panel__chart panel__chart--tall">
          <v-chart v-if="!loading" :option="productOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>

      <article class="panel">
        <h2 class="panel__title">⑦ 订单状态分布</h2>
        <div class="panel__chart panel__chart--tall">
          <v-chart v-if="!loading" :option="statusOption" autoresize />
          <div v-else class="panel__loading">加载中…</div>
        </div>
      </article>
    </section>

  </div>
</template>

<style scoped>
.ops-screen {
  min-height: 100vh;
  padding: 20px 24px 32px;
  background:
    radial-gradient(ellipse at 20% 0%, rgba(14, 165, 233, 0.12), transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(52, 211, 153, 0.08), transparent 45%),
    var(--bg-deep);
}

.ops-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-glow);
}

.ops-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ops-header__left h1 {
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.ops-badge {
  padding: 4px 10px;
  border: 1px solid var(--border-glow);
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--accent-cyan);
}

.ops-header__center {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.ops-header__center label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.ops-header__center input[type='date'] {
  background: var(--bg-panel);
  border: 1px solid var(--border-glow);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: 6px;
}

.btn {
  padding: 8px 14px;
  border: 1px solid var(--accent-cyan);
  background: rgba(56, 189, 248, 0.15);
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn--ghost {
  border-color: var(--text-muted);
  background: transparent;
}

.ops-header__right {
  text-align: right;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.ops-error {
  display: block;
  color: var(--accent-rose);
  margin-top: 4px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 18px;
}

.kpi-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-glow);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: inset 0 0 24px rgba(56, 189, 248, 0.04);
}

.kpi-card--accent {
  border-color: rgba(52, 211, 153, 0.45);
}

.kpi-card__label {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.kpi-card__value {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--accent-cyan);
}

.kpi-card--accent .kpi-card__value {
  color: var(--accent-green);
}

.kpi-card__sub {
  margin-top: 6px;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.kpi-card__sub.up {
  color: var(--accent-green);
}

.kpi-card__sub.down {
  color: var(--accent-rose);
}

.grid-2x2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-glow);
  border-radius: 10px;
  padding: 14px 16px 10px;
  min-height: 280px;
}

.panel--wide {
  grid-column: span 2;
}

.panel__title {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid var(--accent-cyan);
}

.panel__chart {
  height: 220px;
}

.panel__chart--tall {
  height: 260px;
}

.panel__loading {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.ops-footer {
  margin-top: 18px;
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-muted);
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .grid-2x2 {
    grid-template-columns: 1fr;
  }

  .panel--wide {
    grid-column: span 1;
  }

  .ops-header {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .ops-header__right {
    text-align: center;
  }
}
</style>
