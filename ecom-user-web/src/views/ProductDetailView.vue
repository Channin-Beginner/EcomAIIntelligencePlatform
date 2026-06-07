<template>
  <div v-if="loading" class="muted">加载中...</div>
  <div v-else-if="error" class="error">{{ error }}</div>
  <div v-else-if="product" class="detail-page">
    <div class="panel detail-layout">
      <img class="detail-img" :src="product.pic || placeholder" :alt="product.name" />
      <div>
        <h1>{{ product.name }}</h1>
        <p class="muted">{{ product.sub_title }}</p>
        <p class="price detail-price">¥{{ formatPrice(product.price) }}</p>
        <p>销量 {{ product.sale || 0 }} · 库存 {{ product.stock || 0 }}</p>
        <div class="qty-row">
          <label>数量</label>
          <input v-model.number="quantity" type="number" min="1" />
        </div>
        <div class="actions">
          <button class="btn" @click="addCart">加入购物车</button>
          <button class="btn secondary" @click="buyNow">立即购买</button>
          <button
            type="button"
            class="btn fav-btn"
            :class="{ collected: isCollected }"
            :disabled="favLoading"
            @click="toggleFavorite"
          >
            {{ isCollected ? '已收藏' : '收藏' }}
          </button>
        </div>
        <p v-if="message" :class="messageOk ? 'muted' : 'error'">{{ message }}</p>
      </div>
    </div>

    <section v-if="similarProducts.length" class="panel strip-section detail-similar">
      <div class="strip-head">
        <h2>看了又看</h2>
        <span class="muted">相关商品推荐</span>
      </div>
      <div class="strip-scroll">
        <ProductCard
          v-for="p in similarProducts"
          :key="'sim-' + p.id"
          :product="p"
          compact
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  addCollection,
  addToCart,
  fetchCollectionStatus,
  fetchProductDetail,
  fetchSimilarProducts,
  removeCollection,
  type Product,
} from '@/api/mall'
import { trackEvent } from '@/api/track'
import ProductCard from '@/components/ProductCard.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const product = ref<Product | null>(null)
const similarProducts = ref<Product[]>([])
const quantity = ref(1)
const loading = ref(true)
const error = ref('')
const message = ref('')
const messageOk = ref(true)
const placeholder = 'https://via.placeholder.com/400x400?text=Product'
const skuId = ref<number | undefined>()
const isCollected = ref(false)
const favLoading = ref(false)

function formatPrice(v?: number) {
  return (v ?? 0).toFixed(2)
}

async function loadProduct(productId: number) {
  loading.value = true
  error.value = ''
  message.value = ''
  product.value = null
  similarProducts.value = []
  quantity.value = 1
  isCollected.value = false
  window.scrollTo({ top: 0, behavior: 'smooth' })

  try {
    const [detailRes, similarRes] = await Promise.all([
      fetchProductDetail(productId),
      fetchSimilarProducts(productId, 10).catch(() => null),
    ])
    const data = detailRes.data as { product: Product; skuStockList?: { id: number }[] }
    product.value = data.product
    skuId.value = data.skuStockList?.[0]?.id
    similarProducts.value = similarRes?.data?.list ?? []
    trackEvent('pv', productId).catch(() => {})
    if (userStore.token) {
      fetchCollectionStatus(productId)
        .then(res => {
          isCollected.value = res.data.collected
        })
        .catch(() => {})
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.id,
  id => {
    const productId = Number(id)
    if (!Number.isFinite(productId) || productId <= 0) return
    loadProduct(productId)
  },
  { immediate: true },
)

async function addCart() {
  if (!userStore.token) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  try {
    await addToCart(product.value!.id, skuId.value, quantity.value)
    message.value = '已加入购物车'
    messageOk.value = true
  } catch (e) {
    message.value = e instanceof Error ? e.message : '加购失败'
    messageOk.value = false
  }
}

async function buyNow() {
  await addCart()
  if (messageOk.value) router.push('/cart')
}

async function toggleFavorite() {
  if (!userStore.token) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  if (!product.value) return
  favLoading.value = true
  try {
    if (isCollected.value) {
      await removeCollection(product.value.id)
      isCollected.value = false
      message.value = '已取消收藏'
    } else {
      await addCollection(product.value.id)
      isCollected.value = true
      message.value = '已加入收藏'
    }
    messageOk.value = true
  } catch (e) {
    message.value = e instanceof Error ? e.message : '操作失败'
    messageOk.value = false
  } finally {
    favLoading.value = false
  }
}
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.detail-similar {
  padding: 16px;
}
.detail-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 32px;
}
.detail-img {
  width: 100%;
  border-radius: 12px;
  background: #f8fafc;
}
.detail-price {
  font-size: 28px;
  margin: 16px 0;
}
.qty-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
}
.qty-row input {
  width: 80px;
  padding: 8px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.btn.secondary {
  background: #334155;
}
.btn.fav-btn {
  background: #fff;
  color: var(--text);
  border: 1px solid var(--border);
}
.btn.fav-btn.collected {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #b45309;
}
@media (max-width: 800px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
