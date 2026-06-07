<template>
  <div>
    <h1 class="section-title">搜索：{{ keyword || '全部商品' }}</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="product-grid">
      <ProductCard v-for="p in products" :key="p.id" :product="p" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { searchProducts, type Product } from '@/api/mall'
import ProductCard from '@/components/ProductCard.vue'

const route = useRoute()
const keyword = ref((route.query.keyword as string) || '')
const products = ref<Product[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await searchProducts(keyword.value)
    const data = res.data as { list?: Product[] }
    products.value = data.list || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '搜索失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.query.keyword, v => {
  keyword.value = (v as string) || ''
  load()
})
</script>
