<template>
  <div class="panel">
    <h1>确认订单</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <template v-else>
      <h3>收货地址</h3>
      <div v-if="!addresses.length" class="address-form">
        <p class="muted">暂无地址，请新增</p>
        <div class="form-row"><label>收货人</label><input v-model="form.name" /></div>
        <div class="form-row"><label>手机</label><input v-model="form.phoneNumber" /></div>
        <div class="form-row"><label>省</label><input v-model="form.province" /></div>
        <div class="form-row"><label>市</label><input v-model="form.city" /></div>
        <div class="form-row"><label>区</label><input v-model="form.region" /></div>
        <div class="form-row"><label>详细地址</label><input v-model="form.detailAddress" /></div>
        <button class="btn" @click="saveAddress">保存地址</button>
      </div>
      <div v-else class="address-list">
        <label v-for="addr in addresses" :key="addr.id" class="address-item">
          <input v-model="addressId" type="radio" :value="addr.id" />
          {{ addr.name }} {{ addr.phone_number }} {{ addr.province }}{{ addr.city }}{{ addr.region }}{{ addr.detail_address }}
        </label>
      </div>

      <h3>商品清单</h3>
      <ul>
        <li v-for="item in cartItems" :key="item.id">
          {{ item.product_name }} × {{ item.quantity }} — ¥{{ (item.price * item.quantity).toFixed(2) }}
        </li>
      </ul>
      <p>应付：<strong class="price">¥{{ payAmount.toFixed(2) }}</strong></p>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn" :disabled="submitting" @click="submitOrder">
        {{ submitting ? '提交中...' : '提交订单并模拟支付' }}
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { addAddress, confirmOrder, createOrder, fetchAddressList, payOrder } from '@/api/mall'

interface Address {
  id: number
  name: string
  phone_number: string
  province: string
  city: string
  region: string
  detail_address: string
}

interface CartItem {
  id: number
  product_name: string
  price: number
  quantity: number
}

const router = useRouter()
const cartIds = JSON.parse(sessionStorage.getItem('checkout_cart_ids') || '[]') as number[]
const addresses = ref<Address[]>([])
const cartItems = ref<CartItem[]>([])
const addressId = ref<number | null>(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const form = ref({
  name: '测试用户',
  phoneNumber: '18000000000',
  province: '上海市',
  city: '上海市',
  region: '浦东新区',
  detailAddress: '张江路 100 号',
  defaultStatus: 1,
})

const payAmount = computed(() =>
  cartItems.value.reduce((s, i) => s + i.price * i.quantity, 0),
)

onMounted(async () => {
  const [addrRes, confirmRes] = await Promise.all([
    fetchAddressList(),
    confirmOrder(cartIds),
  ])
  addresses.value = (addrRes.data as Address[]) || []
  if (addresses.value.length) addressId.value = addresses.value[0].id
  const confirm = confirmRes.data as { cartPromotionItemList?: CartItem[] }
  cartItems.value = confirm.cartPromotionItemList || []
  loading.value = false
})

async function saveAddress() {
  await addAddress(form.value)
  const res = await fetchAddressList()
  addresses.value = (res.data as Address[]) || []
  if (addresses.value.length) addressId.value = addresses.value[addresses.value.length - 1].id
}

async function submitOrder() {
  if (!addressId.value) {
    error.value = '请选择或新增收货地址'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const res = await createOrder({
      memberReceiveAddressId: addressId.value,
      payType: 1,
      cartIds,
    })
    const data = res.data as { order: { id: number } }
    await payOrder(data.order.id, 1)
    sessionStorage.removeItem('checkout_cart_ids')
    router.push('/orders')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '下单失败'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.address-item {
  display: block;
  margin-bottom: 8px;
}
.address-form {
  margin-bottom: 24px;
}
</style>
