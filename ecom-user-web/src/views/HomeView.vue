<template>
  <div v-if="loading" class="muted home-loading">加载中...</div>
  <div v-else-if="error" class="error">{{ error }}</div>
  <div v-else class="home-page">
    <!-- 顶部三栏：分类 | 轮播 | 品牌/活动 -->
    <section class="home-hero">
      <aside class="category-sidebar panel">
        <div class="sidebar-title">全部商品分类</div>
        <ul class="category-list">
          <li
            v-for="cat in categories"
            :key="cat.id"
            :class="{ active: activeCategoryId === cat.id, hover: hoveredCategoryId === cat.id }"
            @mouseenter="hoveredCategoryId = cat.id"
            @mouseleave="hoveredCategoryId = null"
            @click="selectCategory(cat.id)"
          >
            <span>{{ cat.name }}</span>
            <small v-if="cat.product_count">{{ cat.product_count }}件</small>
          </li>
        </ul>
      </aside>

      <div class="hero-banner panel">
        <div v-if="advertises.length" class="carousel">
          <a
            v-for="(ad, idx) in advertises"
            :key="ad.id"
            class="carousel-slide"
            :class="{ active: carouselIndex === idx }"
            href="#"
            @click.prevent
          >
            <img v-if="ad.pic" :src="ad.pic" :alt="ad.name" />
            <div v-else class="carousel-fallback">{{ ad.name }}</div>
          </a>
          <div v-if="advertises.length > 1" class="carousel-dots">
            <button
              v-for="(_, idx) in advertises"
              :key="idx"
              type="button"
              :class="{ active: carouselIndex === idx }"
              @click="carouselIndex = idx"
            />
          </div>
        </div>
        <div v-else class="carousel-fallback hero-placeholder">EcomAI 数码好物节</div>
      </div>

      <aside class="hero-side">
        <div class="side-card panel">
          <h4>热销爆款</h4>
          <p class="side-desc">按销量实时更新</p>
          <button type="button" class="btn btn-sm" @click="selectTab('hot')">去看看</button>
        </div>
        <div class="side-card panel">
          <h4>在售商品</h4>
          <p class="side-stat">{{ totalProductCount }}</p>
          <span class="muted">件好物等你挑</span>
        </div>
        <div v-if="brands.length" class="side-brands panel">
          <h4>品牌精选</h4>
          <div class="brand-chips">
            <RouterLink
              v-for="b in brands.slice(0, 6)"
              :key="b.id"
              :to="{ name: 'brand', params: { id: b.id } }"
              class="brand-chip"
            >
              {{ b.name }}
            </RouterLink>
          </div>
        </div>
      </aside>
    </section>

    <!-- 横滑专区：热销 -->
    <section v-if="hotProducts.length" class="strip-section panel">
      <div class="strip-head">
        <h2>京东秒杀 · 热销榜</h2>
        <button type="button" class="link-more" @click="selectTab('hot')">查看更多 ›</button>
      </div>
      <div class="strip-scroll">
        <ProductCard
          v-for="p in hotProducts"
          :key="'hot-' + p.id"
          :product="p"
          compact
        />
      </div>
    </section>

    <!-- 横滑专区：新品 -->
    <section v-if="newProducts.length" class="strip-section panel">
      <div class="strip-head">
        <h2>新品首发</h2>
        <button type="button" class="link-more" @click="selectTab('new')">查看更多 ›</button>
      </div>
      <div class="strip-scroll">
        <ProductCard
          v-for="p in newProducts"
          :key="'new-' + p.id"
          :product="p"
          compact
        />
      </div>
    </section>

    <!-- 为你推荐：Tab + 瀑布网格 -->
    <section
      ref="feedSectionRef"
      class="feed-section panel"
      :class="{ 'feed-highlight': feedHighlight }"
    >
      <div class="feed-head">
        <h2>{{ feedTitle }}</h2>
        <span v-if="forYouHint" class="muted">{{ forYouHint }}</span>
        <span v-else class="muted">共 {{ feedTotal }} 件商品</span>
      </div>

      <div class="feed-tabs" role="tablist">
        <button
          v-for="t in feedTabs"
          :key="t.key"
          type="button"
          role="tab"
          class="feed-tab"
          :class="{ active: activeTab === t.key && !activeCategoryId }"
          @click="selectTab(t.key)"
        >
          {{ t.label }}
        </button>
        <button
          v-for="cat in categories"
          :key="'cat-' + cat.id"
          type="button"
          role="tab"
          class="feed-tab"
          :class="{ active: activeCategoryId === cat.id }"
          @click="selectCategory(cat.id)"
        >
          {{ cat.name }}
        </button>
      </div>

      <div v-if="feedLoading && !feedProducts.length" class="muted feed-loading">加载商品...</div>
      <div v-else-if="feedError" class="error">{{ feedError }}</div>
      <div v-else class="feed-grid">
        <ProductCard v-for="p in feedProducts" :key="p.id" :product="p" />
      </div>

      <div v-if="feedProducts.length" class="feed-footer">
        <p class="muted">
          已显示 {{ feedProducts.length }} / {{ feedTotal }} 件
          <template v-if="isForYouTab && forYouHint"> · 匹配度由高到低</template>
        </p>
        <button
          v-if="hasMore"
          type="button"
          class="btn load-more-btn"
          :disabled="feedLoading"
          @click="loadMore"
        >
          {{ feedLoading ? '加载中...' : '加载更多' }}
        </button>
        <p v-else class="muted">没有更多了</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  fetchForYouFeed,
  fetchHomeContent,
  fetchProductFeed,
  type Brand,
  type HomeCategory,
  type Product,
} from '@/api/mall'
import { useUserStore } from '@/stores/user'
import ProductCard from '@/components/ProductCard.vue'

type FeedTab = 'all' | 'hot' | 'new' | 'recommend'

const loading = ref(true)
const error = ref('')
const advertises = ref<{ id: number; name: string; pic?: string }[]>([])
const brands = ref<Brand[]>([])
const userStore = useUserStore()
const hotProducts = ref<Product[]>([])
const newProducts = ref<Product[]>([])
const forYouHint = ref('')
const categories = ref<HomeCategory[]>([])
const totalProductCount = ref(0)

const carouselIndex = ref(0)
let carouselTimer: ReturnType<typeof setInterval> | undefined

const feedTabs: { key: FeedTab; label: string }[] = [
  { key: 'all', label: '为你推荐' },
  { key: 'hot', label: '热销榜' },
  { key: 'new', label: '新品' },
  { key: 'recommend', label: '精品优选' },
]

const activeTab = ref<FeedTab>('all')
const activeCategoryId = ref<number | null>(null)
const hoveredCategoryId = ref<number | null>(null)
const feedSectionRef = ref<HTMLElement | null>(null)
const feedHighlight = ref(false)
const feedProducts = ref<Product[]>([])
const feedTotal = ref(0)
const feedPage = ref(1)
const feedLoading = ref(false)
const feedError = ref('')
const pageSize = 20

const hasMore = computed(() => feedProducts.value.length < feedTotal.value)

const isForYouTab = computed(
  () => activeTab.value === 'all' && activeCategoryId.value === null,
)

const feedTitle = computed(() => {
  if (activeCategoryId.value) {
    const cat = categories.value.find(c => c.id === activeCategoryId.value)
    return cat ? `${cat.name}` : '分类商品'
  }
  const tab = feedTabs.find(t => t.key === activeTab.value)
  return tab?.label ?? '为你推荐'
})

let highlightTimer: ReturnType<typeof setTimeout> | undefined

async function scrollToFeed() {
  await nextTick()
  feedSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  feedHighlight.value = true
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => {
    feedHighlight.value = false
  }, 1400)
}

function startCarousel() {
  if (advertises.value.length <= 1) return
  carouselTimer = setInterval(() => {
    carouselIndex.value = (carouselIndex.value + 1) % advertises.value.length
  }, 4000)
}

async function loadFeed(reset = false) {
  if (reset) {
    feedPage.value = 1
    feedProducts.value = []
    if (isForYouTab.value) {
      forYouHint.value = ''
    }
  }
  feedLoading.value = true
  feedError.value = ''
  try {
    if (isForYouTab.value) {
      const res = await fetchForYouFeed(feedPage.value, pageSize)
      const data = res.data
      feedTotal.value = data.total
      if (data.strategy === 'itemcf_personal') {
        forYouHint.value = userStore.nickname
          ? `${userStore.nickname}，按偏好匹配度排序 · 共 ${data.total} 件`
          : `按你的偏好匹配度排序 · 共 ${data.total} 件`
      } else {
        forYouHint.value = `热销精选 · 共 ${data.total} 件`
      }
      if (reset) {
        feedProducts.value = data.list
      } else {
        feedProducts.value = [...feedProducts.value, ...data.list]
      }
    } else {
      const res = await fetchProductFeed({
        tab: activeTab.value,
        categoryId: activeCategoryId.value ?? undefined,
        pageNum: feedPage.value,
        pageSize,
      })
      const data = res.data
      feedTotal.value = data.total
      if (reset) {
        feedProducts.value = data.list
      } else {
        feedProducts.value = [...feedProducts.value, ...data.list]
      }
    }
  } catch (e) {
    feedError.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    feedLoading.value = false
  }
}

async function selectTab(tab: FeedTab) {
  activeTab.value = tab
  activeCategoryId.value = null
  hoveredCategoryId.value = null
  scrollToFeed()
  await loadFeed(true)
}

async function selectCategory(id: number) {
  activeCategoryId.value = id
  activeTab.value = 'all'
  hoveredCategoryId.value = null
  scrollToFeed()
  await loadFeed(true)
}

function loadMore() {
  if (!hasMore.value || feedLoading.value) return
  feedPage.value += 1
  loadFeed(false)
}

onMounted(async () => {
  try {
    const res = await fetchHomeContent()
    const data = res.data
    advertises.value = data.advertiseList || []
    brands.value = data.brandList || []
    hotProducts.value = data.hotProductList || []
    newProducts.value = data.newProductList || []
    categories.value = data.categoryNavList || []
    totalProductCount.value = data.totalProductCount || 0
    startCarousel()
    await loadFeed(true)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (carouselTimer) clearInterval(carouselTimer)
  if (highlightTimer) clearTimeout(highlightTimer)
})
</script>
