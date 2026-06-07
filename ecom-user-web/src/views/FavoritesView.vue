<template>
  <div class="panel">
    <h1>我的收藏</h1>
    <div v-if="loading" class="muted">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="!items.length" class="muted">还没有收藏商品，去逛逛吧</div>
    <div v-else class="product-grid">
      <div v-for="item in items" :key="item.id" class="fav-item">
        <ProductCard :product="item.product" />
        <button type="button" class="btn btn-sm fav-remove" @click="remove(item.productId)">
          取消收藏
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  fetchCollectionList,
  removeCollection,
  type CollectionItem,
} from '@/api/mall'
import ProductCard from '@/components/ProductCard.vue'

const items = ref<CollectionItem[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchCollectionList()
    items.value = res.data
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function remove(productId: number) {
  try {
    await removeCollection(productId)
    items.value = items.value.filter(i => i.productId !== productId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取消收藏失败'
  }
}

onMounted(load)
</script>

<style scoped>
.fav-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fav-remove {
  align-self: flex-start;
  background: #64748b;
}
</style>
