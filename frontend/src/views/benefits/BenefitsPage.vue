<template>
  <div class="benefits-page">
    <h2 class="page-title">福利管理</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="福利项目" name="items">
        <div class="page-actions">
          <el-button type="primary" @click="showItemDialog = true">
            <el-icon><Plus /></el-icon> 新建福利项目
          </el-button>
        </div>
        <el-table :data="benefitItems" v-loading="loadingItems" border>
          <el-table-column prop="name" label="名称" min-width="150" />
          <el-table-column prop="category" label="类别" width="120" />
          <el-table-column prop="annual_budget" label="年度预算" width="120">
            <template #default="{ row }">
              {{ row.annual_budget ? `¥${row.annual_budget.toLocaleString()}` : "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? "启用" : "停用" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" link @click="editItem(row)">编辑</el-button>
              <el-popconfirm title="确定删除?" @confirm="deleteItem(row.id)">
                <template #reference>
                  <el-button size="small" type="danger" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="福利申领" name="claims">
        <div class="page-actions">
          <el-button type="primary" @click="showClaimDialog = true">
            <el-icon><Plus /></el-icon> 提交申领
          </el-button>
        </div>
        <el-table :data="claims" v-loading="loadingClaims" border>
          <el-table-column prop="benefit_item_name" label="福利项目" min-width="150" />
          <el-table-column prop="claim_date" label="申领日期" width="120" />
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">¥{{ row.amount.toLocaleString() }}</template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="200" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'"
                size="small"
              >
                {{ { pending: "待审批", approved: "已通过", rejected: "已驳回" }[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Create/Edit Benefit Item Dialog -->
    <el-dialog v-model="showItemDialog" :title="editingItem ? '编辑福利项目' : '新建福利项目'" width="500px">
      <el-form :model="itemForm" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="itemForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="itemForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="类别">
          <el-input v-model="itemForm.category" placeholder="如: 社保、补贴、商业保险" />
        </el-form-item>
        <el-form-item label="年度预算">
          <el-input-number v-model="itemForm.annual_budget" :min="0" :step="1000" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showItemDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingItem" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>

    <!-- Claim Dialog -->
    <el-dialog v-model="showClaimDialog" title="提交福利申领" width="500px">
      <el-form :model="claimForm" label-width="100px">
        <el-form-item label="福利项目" required>
          <el-select v-model="claimForm.benefit_item_id" style="width: 100%">
            <el-option
              v-for="item in benefitItems"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="申领日期" required>
          <el-date-picker v-model="claimForm.claim_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="claimForm.amount" :min="0" :step="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="claimForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showClaimDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingClaim" @click="submitClaim">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse } from "@/types/auth"
import type { BenefitItem, BenefitItemCreateRequest, BenefitClaim, BenefitClaimCreateRequest } from "@/types/benefits"
import type { PaginatedResponse } from "@/types/hr"

const activeTab = ref("items")
const benefitItems = ref<BenefitItem[]>([])
const claims = ref<BenefitClaim[]>([])
const loadingItems = ref(false)
const loadingClaims = ref(false)
const showItemDialog = ref(false)
const editingItem = ref<BenefitItem | null>(null)
const savingItem = ref(false)
const showClaimDialog = ref(false)
const savingClaim = ref(false)

const itemForm = reactive<BenefitItemCreateRequest>({
  name: "",
  description: "",
  category: "",
  annual_budget: undefined,
})

const claimForm = reactive({
  benefit_item_id: "",
  claim_date: "",
  amount: 0,
  description: "",
})

function resetItemForm() {
  Object.assign(itemForm, { name: "", description: "", category: "", annual_budget: undefined })
  editingItem.value = null
}

function resetClaimForm() {
  Object.assign(claimForm, { benefit_item_id: "", claim_date: "", amount: 0, description: "" })
}

async function loadItems() {
  loadingItems.value = true
  try {
    const res = await http.get<APIResponse<BenefitItem[]>>("/benefits/items")
    benefitItems.value = res.data.data!
  } catch {
    // ignore
  } finally {
    loadingItems.value = false
  }
}

async function loadClaims() {
  loadingClaims.value = true
  try {
    const res = await http.get<APIResponse<{ data: BenefitClaim[] }>>("/benefits/claims?page_size=50")
    claims.value = res.data.data!.data
  } catch {
    // ignore
  } finally {
    loadingClaims.value = false
  }
}

async function saveItem() {
  savingItem.value = true
  try {
    if (editingItem.value) {
      await http.put(`/benefits/items/${editingItem.value.id}`, itemForm)
      ElMessage.success("更新成功")
    } else {
      await http.post("/benefits/items", itemForm)
      ElMessage.success("创建成功")
    }
    showItemDialog.value = false
    resetItemForm()
    loadItems()
  } catch {
    ElMessage.error("保存失败")
  } finally {
    savingItem.value = false
  }
}

function editItem(item: BenefitItem) {
  editingItem.value = item
  Object.assign(itemForm, {
    name: item.name,
    description: item.description || "",
    category: item.category || "",
    annual_budget: item.annual_budget,
  })
  showItemDialog.value = true
}

async function deleteItem(id: string) {
  // Items are soft-deleted via deactivation
  try {
    await http.put(`/benefits/items/${id}`, { is_active: false })
    ElMessage.success("已停用")
    loadItems()
  } catch {
    ElMessage.error("操作失败")
  }
}

async function submitClaim() {
  savingClaim.value = true
  try {
    await http.post("/benefits/claims", claimForm)
    ElMessage.success("申领已提交")
    showClaimDialog.value = false
    resetClaimForm()
    loadClaims()
  } catch {
    ElMessage.error("提交失败")
  } finally {
    savingClaim.value = false
  }
}

onMounted(() => {
  loadItems()
  loadClaims()
})
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 20px;
  font-size: 22px;
  color: #303133;
}
.page-actions {
  margin-bottom: 16px;
}
</style>
