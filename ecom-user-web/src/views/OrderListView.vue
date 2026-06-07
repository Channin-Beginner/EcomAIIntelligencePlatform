<template>
  <div class="panel">
    <h1>我的订单</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <div v-else-if="!orders.length" class="muted">暂无订单</div>
    <div v-for="row in orders" :key="row.order.id" class="order-card">
      <div class="order-head">
        <span>订单号 {{ row.order.order_sn }}</span>
        <span>{{ statusText(row.order.status) }}</span>
      </div>
      <ul>
        <li v-for="item in row.orderItemList" :key="item.id">
          {{ item.product_name }} × {{ item.product_quantity }} — ¥{{ item.product_price }}
        </li>
      </ul>
      <p>实付 ¥{{ row.order.pay_amount }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchOrders } from '@/api/mall'

interface OrderRow {
  order: { id: number; order_sn: string; status: number; pay_amount: number }
  orderItemList: { id: number; product_name: string; product_quantity: number; product_price: number }[]
}

const orders = ref<OrderRow[]>([])
const loading = ref(true)

const statusMap: Record<number, string> = {
  0: '待付款',
  1: '待发货',
  2: '已发货',
  3: '已完成',
  4: '已关闭',
}

function statusText(s: number) {
  return statusMap[s] || '未知'
}

onMounted(async () => {
  const res = await fetchOrders(-1, 1, 20)
  const data = res.data as { list?: OrderRow[] }
  orders.value = data.list || []
  loading.value = false
})
</script>

<style scoped>
.order-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.order-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
