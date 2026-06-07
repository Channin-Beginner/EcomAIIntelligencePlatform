<template>
  <div class="panel">
    <h1>购物车</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <div v-else-if="!items.length" class="muted">购物车是空的</div>
    <table v-else class="table">
      <thead>
        <tr>
          <th><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
          <th>商品</th>
          <th>单价</th>
          <th>数量</th>
          <th>小计</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td><input v-model="selected" type="checkbox" :value="item.id" /></td>
          <td>{{ item.product_name }}</td>
          <td>¥{{ item.price }}</td>
          <td>
            <input
              type="number"
              min="1"
              :value="item.quantity"
              @change="onQtyChange(item.id, $event)"
            />
          </td>
          <td>¥{{ (item.price * item.quantity).toFixed(2) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-if="items.length" class="cart-footer">
      <p>已选 {{ selected.length }} 件，合计 <strong class="price">¥{{ total.toFixed(2) }}</strong></p>
      <button class="btn" :disabled="!selected.length" @click="goCheckout">去结算</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCartList, updateCartQuantity } from '@/api/mall'

interface CartItem {
  id: number
  product_name: string
  price: number
  quantity: number
}

const router = useRouter()
const items = ref<CartItem[]>([])
const selected = ref<number[]>([])
const loading = ref(true)

const allSelected = computed(() => items.value.length > 0 && selected.value.length === items.value.length)
const total = computed(() =>
  items.value.filter(i => selected.value.includes(i.id)).reduce((s, i) => s + i.price * i.quantity, 0),
)

onMounted(async () => {
  const res = await fetchCartList()
  items.value = (res.data as CartItem[]) || []
  selected.value = items.value.map(i => i.id)
  loading.value = false
})

function toggleAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  selected.value = checked ? items.value.map(i => i.id) : []
}

async function onQtyChange(id: number, e: Event) {
  const qty = Number((e.target as HTMLInputElement).value)
  await updateCartQuantity(id, qty)
  const item = items.value.find(i => i.id === id)
  if (item) item.quantity = qty
}

function goCheckout() {
  sessionStorage.setItem('checkout_cart_ids', JSON.stringify(selected.value))
  router.push('/checkout')
}
</script>

<style scoped>
.cart-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}
</style>
