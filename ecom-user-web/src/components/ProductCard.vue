<template>
  <article class="product-card" :class="{ compact }" @click="goDetail">
    <div class="thumb">
      <img :src="product.pic || placeholder" :alt="product.name" />
    </div>
    <h3>{{ product.name }}</h3>
    <p class="sub">{{ product.sub_title }}</p>
    <div class="meta">
      <span class="price">¥{{ formatPrice(product.price) }}</span>
      <span v-if="product.sale" class="sale">已售 {{ product.sale }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Product } from '@/api/mall'
import { trackEvent } from '@/api/track'

const props = withDefaults(defineProps<{ product: Product; compact?: boolean }>(), {
  compact: false,
})
const router = useRouter()
const placeholder = 'https://via.placeholder.com/240x240?text=Product'

function formatPrice(v?: number) {
  return (v ?? 0).toFixed(2)
}

function goDetail() {
  const id = props.product.id
  if (!id) return
  router.push({ name: 'product', params: { id } })
  trackEvent('click', id).catch(() => {})
}
</script>
