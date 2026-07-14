<template>
  <div class="employee-list-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">员工管理</span>
          <el-button type="primary" @click="showCreate = true">
            <el-icon><Plus /></el-icon>添加员工
          </el-button>
        </div>
      </template>

      <!-- Filters -->
      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 130px">
            <el-option label="在职" value="active" />
            <el-option label="试用期" value="probation" />
            <el-option label="离职" value="resigned" />
            <el-option label="停职" value="suspended" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="filters.search"
            placeholder="姓名/工号/邮箱"
            clearable
            style="width: 220px"
            @keyup.enter="loadEmployees"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadEmployees">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- Table -->
      <el-table :data="employees" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="display_name" label="姓名" width="140" />
        <el-table-column label="部门" width="160">
          <template #default="{ row }">
            {{ row.department_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="岗位" width="160">
          <template #default="{ row }">
            {{ row.position_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="employment_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.employment_type === 'full_time' ? '' : 'warning'" size="small">
              {{ typeLabel(row.employment_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hire_date" label="入职日期" width="120" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewEmployee(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadEmployees"
        />
      </div>
    </el-card>

    <!-- Create Employee Dialog -->
    <el-dialog v-model="showCreate" title="添加员工" width="600px" :close-on-click-modal="false">
      <el-form :model="createForm" label-width="100px" :rules="createRules" ref="createFormRef">
        <el-form-item label="用户ID" prop="user_id">
          <el-input v-model="createForm.user_id" placeholder="关联用户ID" />
        </el-form-item>
        <el-form-item label="工号" prop="employee_no">
          <el-input v-model="createForm.employee_no" placeholder="例如: E001" />
        </el-form-item>
        <el-form-item label="部门ID">
          <el-input v-model="createForm.department_id" placeholder="部门ID（可选）" />
        </el-form-item>
        <el-form-item label="岗位ID">
          <el-input v-model="createForm.position_id" placeholder="岗位ID（可选）" />
        </el-form-item>
        <el-form-item label="汇报上级">
          <el-input v-model="createForm.reports_to" placeholder="上级ID（可选）" />
        </el-form-item>
        <el-form-item label="入职日期" prop="hire_date">
          <el-date-picker v-model="createForm.hire_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="雇佣类型">
          <el-select v-model="createForm.employment_type" style="width: 100%">
            <el-option label="全职" value="full_time" />
            <el-option label="兼职" value="part_time" />
            <el-option label="合同" value="contract" />
            <el-option label="实习" value="intern" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作地点">
          <el-input v-model="createForm.work_location" placeholder="工作地点（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, PaginatedResponse, EmployeeBasic, EmployeeCreateRequest } from "@/types/hr"

const router = useRouter()
const loading = ref(false)
const employees = ref<EmployeeBasic[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filters = reactive({
  status: "",
  search: "",
})

const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive<EmployeeCreateRequest>({
  user_id: "",
  employee_no: "",
  department_id: "",
  position_id: "",
  reports_to: "",
  hire_date: "",
  employment_type: "full_time",
  work_location: "",
})

const createRules = {
  user_id: [{ required: true, message: "请输入用户ID", trigger: "blur" }],
  employee_no: [{ required: true, message: "请输入工号", trigger: "blur" }],
  hire_date: [{ required: true, message: "请选择入职日期", trigger: "change" }],
}

async function loadEmployees() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search

    const res = await http.get<APIResponse<PaginatedResponse<EmployeeBasic>>>("/hr/employees", { params })
    if (res.data.data) {
      employees.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch (err: any) {
    ElMessage.error("加载员工列表失败")
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = ""
  filters.search = ""
  page.value = 1
  loadEmployees()
}

function viewEmployee(id: string) {
  router.push(`/hr/employees/${id}`)
}

async function submitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const payload = { ...createForm }
    if (payload.hire_date) {
      payload.hire_date = typeof payload.hire_date === "string" ? payload.hire_date : (payload.hire_date as any).toISOString().split("T")[0]
    }
    await http.post("/hr/employees", payload)
    ElMessage.success("员工创建成功")
    showCreate.value = false
    loadEmployees()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || "创建失败")
  } finally {
    creating.value = false
  }
}

function statusType(s: string) {
  const map: Record<string, string> = { active: "success", probation: "warning", resigned: "info", suspended: "danger" }
  return map[s] || "info"
}

function statusLabel(s: string) {
  const map: Record<string, string> = { active: "在职", probation: "试用期", resigned: "离职", suspended: "停职" }
  return map[s] || s
}

function typeLabel(t: string) {
  const map: Record<string, string> = { full_time: "全职", part_time: "兼职", contract: "合同", intern: "实习" }
  return map[t] || t
}

onMounted(loadEmployees)
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}

.filter-bar {
  margin-bottom: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
