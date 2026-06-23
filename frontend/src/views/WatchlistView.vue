<script setup lang="ts">
/**
 * 自选股管理页面
 *
 * 分组标签页切换 + 股票列表表格 + 搜索添加弹窗
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWatchlistStore } from '@/stores/watchlist'
import { searchStocks, updateWatchlistGroup } from '@/api/index'
import type { StockSearchResult } from '@/types/watchlist'

const router = useRouter()
const store = useWatchlistStore()

// 当前选中的tab："all" 或 分组ID
const activeTab = ref<string>('all')

// 新建分组弹窗
const showCreateGroup = ref(false)
const newGroupName = ref('')

// 搜索添加股票弹窗
const showAddStock = ref(false)
const searchKeyword = ref('')
const searchResults = ref<StockSearchResult[]>([])
const searchLoading = ref(false)
const addNote = ref('')
const selectedStock = ref<StockSearchResult | null>(null)

// 编辑分组弹窗
const showEditGroup = ref(false)
const editGroupForm = ref({ id: 0, name: '', description: '' })

onMounted(async () => {
  await store.fetchGroups()
  await store.fetchStocks(null)
})

function parseGroupId(tab: string): number | null {
  const parsed = Number.parseInt(tab, 10)
  return Number.isNaN(parsed) ? null : parsed
}

// 切换 tab 时加载对应数据
watch(activeTab, async (tab) => {
  if (tab === 'all') {
    store.currentGroupId = null
    await store.fetchStocks(null)
  } else {
    const groupId = parseGroupId(tab)
    store.currentGroupId = groupId
    await store.fetchStocks(groupId)
  }
})

// 搜索股票（输入防抖）
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!searchKeyword.value.trim()) {
      searchResults.value = []
      return
    }
    searchLoading.value = true
    try {
      searchResults.value = await searchStocks(searchKeyword.value)
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

onUnmounted(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
})

function selectSearchResult(stock: StockSearchResult) {
  selectedStock.value = stock
}

async function handleAddStock() {
  if (!selectedStock.value) {
    ElMessage.warning('请先搜索并选择一只股票')
    return
  }
  // 如果在"全部"tab，需要先选择分组
  const targetGroupId = activeTab.value !== 'all' ? parseGroupId(activeTab.value) : null
  if (targetGroupId == null) {
    if (store.groups.length === 0) {
      ElMessage.warning('请先创建一个分组')
      return
    }
    ElMessage.warning('请先切换到一个具体分组，再添加股票')
    return
  }

  try {
    const added = await store.addStock(targetGroupId, selectedStock.value.ts_code, addNote.value)
    if (!added) {
      ElMessage.error('添加失败')
      return
    }
    ElMessage.success(`已添加 ${selectedStock.value.name}`)
    showAddStock.value = false
    resetAddDialog()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '添加失败')
  }
}

function resetAddDialog() {
  searchKeyword.value = ''
  searchResults.value = []
  selectedStock.value = null
  addNote.value = ''
}

async function handleCreateGroup() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  try {
    const created = await store.addGroup(newGroupName.value.trim())
    if (!created) {
      ElMessage.error('创建失败')
      return
    }
    ElMessage.success('分组创建成功')
    showCreateGroup.value = false
    newGroupName.value = ''
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

function openEditGroup(groupId: number) {
  const group = store.groups.find((g) => g.id === groupId)
  if (!group) return
  editGroupForm.value = { id: group.id, name: group.name, description: group.description }
  showEditGroup.value = true
}

async function handleEditGroup() {
  try {
    await updateWatchlistGroup(editGroupForm.value.id, {
      name: editGroupForm.value.name,
      description: editGroupForm.value.description,
    })
    ElMessage.success('分组已更新')
    showEditGroup.value = false
    await store.fetchGroups()
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '更新失败')
  }
}

async function confirmDeleteGroup(groupId: number) {
  const group = store.groups.find((g) => g.id === groupId)
  if (!group) return
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${group.name}」？分组内的 ${group.stock_count} 只股票也会被移除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', confirmButtonClass: 'el-button--danger' },
    )
    const removed = await store.removeGroup(groupId)
    if (!removed) {
      ElMessage.error('删除分组失败')
      return
    }
    activeTab.value = 'all'
    ElMessage.success('已删除')
  } catch (error: unknown) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error instanceof Error ? error.message : '删除分组失败')
  }
}

async function handleRemoveStock(tsCode: string) {
  if (activeTab.value === 'all') return
  const groupId = parseGroupId(activeTab.value)
  if (groupId == null) {
    ElMessage.error('分组 ID 无效')
    return
  }
  try {
    const removed = await store.removeStock(groupId, tsCode)
    if (!removed) {
      ElMessage.error('移除失败')
      return
    }
    ElMessage.success('已移除')
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '移除失败')
  }
}

function goStockDetail(tsCode: string) {
  router.push(`/stock/${tsCode}`)
}

function formatPctChg(val: number | null): string {
  if (val == null) return '-'
  return (val > 0 ? '+' : '') + val.toFixed(2) + '%'
}

function pctChgColor(val: number | null): string {
  if (val == null) return ''
  return val > 0 ? '#ec0000' : val < 0 ? '#00da3c' : ''
}
</script>

<template>
  <div class="watchlist-view">
    <div class="page-header">
      <div>
        <h2 class="page-title">自选股</h2>
        <p class="page-desc">管理你关注的股票，分组整理，快速查看行情</p>
      </div>
      <div class="header-actions">
        <el-button @click="showCreateGroup = true">新建分组</el-button>
        <el-button type="primary" @click="showAddStock = true" :disabled="activeTab === 'all' && store.groups.length === 0">
          添加股票
        </el-button>
      </div>
    </div>

    <!-- 分组标签页 -->
    <el-tabs v-model="activeTab" class="group-tabs">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane v-for="g in store.groups" :key="g.id" :name="String(g.id)">
        <template #label>
          <div class="tab-label">
            <span>{{ g.name }}（{{ g.stock_count }}）</span>
            <el-dropdown trigger="click" @command="(cmd: string) => cmd === 'edit' ? openEditGroup(g.id) : confirmDeleteGroup(g.id)">
              <span class="tab-more" @click.stop>&hellip;</span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">编辑</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- 股票列表 -->
    <el-table
      :data="store.stocks"
      v-loading="store.loading"
      stripe
      empty-text="暂无自选股，点击「添加股票」开始"
      style="width: 100%"
    >
      <el-table-column label="代码" width="110">
        <template #default="{ row }">
          <a class="stock-link" @click="goStockDetail(row.ts_code)">{{ row.ts_code }}</a>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="100" />
      <el-table-column prop="industry" label="行业" width="90" />
      <el-table-column label="最新价" width="90" align="right">
        <template #default="{ row }">{{ row.close ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="100" align="right">
        <template #default="{ row }">
          <span :style="{ color: pctChgColor(row.pct_chg) }">
            {{ formatPctChg(row.pct_chg) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="成交额(亿)" width="110" align="right">
        <template #default="{ row }">{{ row.amount_yi ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="总市值(亿)" width="110" align="right">
        <template #default="{ row }">{{ row.total_mv_yi ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="goStockDetail(row.ts_code)">
            K线
          </el-button>
          <el-button
            v-if="activeTab !== 'all'"
            size="small"
            link
            type="danger"
            @click="handleRemoveStock(row.ts_code)"
          >
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建分组弹窗 -->
    <el-dialog v-model="showCreateGroup" title="新建分组" width="400px">
      <el-input v-model="newGroupName" placeholder="分组名称，如：重点关注" maxlength="30" />
      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑分组弹窗 -->
    <el-dialog v-model="showEditGroup" title="编辑分组" width="400px">
      <el-form label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="editGroupForm.name" maxlength="30" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editGroupForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditGroup = false">取消</el-button>
        <el-button type="primary" @click="handleEditGroup">保存</el-button>
      </template>
    </el-dialog>

    <!-- 搜索添加股票弹窗 -->
    <el-dialog v-model="showAddStock" title="搜索并添加股票" width="500px" @close="resetAddDialog">
      <div class="search-section">
        <el-input
          v-model="searchKeyword"
          placeholder="输入股票代码或名称，如 000001 或 平安"
          @input="onSearchInput"
          clearable
        />
        <div class="search-results" v-if="searchResults.length > 0">
          <div
            v-for="s in searchResults"
            :key="s.ts_code"
            class="search-item"
            :class="{ selected: selectedStock?.ts_code === s.ts_code }"
            @click="selectSearchResult(s)"
          >
            <span class="search-code">{{ s.ts_code }}</span>
            <span class="search-name">{{ s.name }}</span>
            <span class="search-industry">{{ s.industry }}</span>
          </div>
        </div>
        <div v-else-if="searchKeyword && !searchLoading" class="search-empty">
          未找到匹配的股票
        </div>
      </div>
      <div v-if="selectedStock" class="selected-info">
        已选择：<strong>{{ selectedStock.name }}（{{ selectedStock.ts_code }}）</strong>
      </div>
      <el-input
        v-model="addNote"
        placeholder="备注（可选）：为什么关注这只股票"
        style="margin-top: 12px"
      />
      <template #footer>
        <el-button @click="showAddStock = false">取消</el-button>
        <el-button type="primary" @click="handleAddStock" :disabled="!selectedStock">
          添加到当前分组
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.watchlist-view {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 6px;
  color: #303133;
}

.page-desc {
  color: #909399;
  margin: 0;
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.group-tabs {
  margin-bottom: 16px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tab-more {
  cursor: pointer;
  color: #909399;
  font-size: 14px;
  padding: 0 4px;
  line-height: 1;
}

.tab-more:hover {
  color: #409eff;
}

.stock-link {
  color: #409eff;
  cursor: pointer;
  font-family: monospace;
}

.stock-link:hover {
  text-decoration: underline;
}

/* 搜索弹窗样式 */
.search-section {
  margin-bottom: 12px;
}

.search-results {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-top: 8px;
}

.search-item {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  gap: 12px;
  align-items: center;
  transition: background 0.15s;
}

.search-item:hover {
  background: #f5f7fa;
}

.search-item.selected {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.search-code {
  font-family: monospace;
  color: #303133;
  width: 100px;
}

.search-name {
  color: #606266;
  flex: 1;
}

.search-industry {
  color: #909399;
  font-size: 12px;
}

.search-empty {
  color: #909399;
  text-align: center;
  padding: 16px 0;
  font-size: 13px;
}

.selected-info {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 4px;
  font-size: 13px;
}
</style>
