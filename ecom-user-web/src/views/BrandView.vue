<template>
  <div>
    <h1 class="section-title">品牌商品</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <div v-else class="product-grid">
      <ProductCard v-for="p in products" :key="p.id" :product="p" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchBrandProducts, type Product } from '@/api/mall'
import ProductCard from '@/components/ProductCard.vue'

const route = useRoute()
const products = ref<Product[]>([])
const loading = ref(true)

onMounted(async () => {
  const res = await fetchBrandProducts(Number(route.params.id))
  const data = res.data as { list?: Product[] }
  products.value = data.list || []
  loading.value = false
})
</script>
