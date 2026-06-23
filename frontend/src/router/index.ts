import { createRouter, createWebHistory } from 'vue-router'

const DashboardView = () => import('../views/DashboardView.vue')
const HomeView = () => import('../views/HomeView.vue')
const WatchlistView = () => import('../views/WatchlistView.vue')
const ScreeningView = () => import('../views/ScreeningView.vue')
const StrategiesView = () => import('../views/StrategiesView.vue')
const StrategyDetailView = () => import('../views/StrategyDetailView.vue')
const StockDetailView = () => import('../views/StockDetailView.vue')
const AnalysisView = () => import('../views/AnalysisView.vue')
const SentimentView = () => import('../views/SentimentView.vue')
const PlanView = () => import('../views/PlanView.vue')
const PlanGenerateView = () => import('../views/PlanGenerateView.vue')
const TradeView = () => import('../views/TradeView.vue')
const PositionView = () => import('../views/PositionView.vue')
const ReviewView = () => import('../views/ReviewView.vue')
const SettingsView = () => import('../views/SettingsView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: DashboardView },
    { path: '/home', name: 'home-legacy', component: HomeView },
    { path: '/watchlist', name: 'watchlist', component: WatchlistView },
    { path: '/screening', name: 'screening', component: ScreeningView },
    { path: '/strategies', name: 'strategies', component: StrategiesView },
    { path: '/strategies/:id', name: 'strategy-detail', component: StrategyDetailView },
    { path: '/stock/:tsCode', name: 'stock-detail', component: StockDetailView },
    { path: '/analysis', name: 'analysis', component: AnalysisView },
    { path: '/sentiment', name: 'sentiment', component: SentimentView },
    { path: '/plan', name: 'plan', component: PlanView },
    { path: '/plan/generate/:tsCode', name: 'plan-generate', component: PlanGenerateView },
    { path: '/trade', name: 'trade', component: TradeView },
    { path: '/position', name: 'position', component: PositionView },
    { path: '/review', name: 'review', component: ReviewView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

export default router
