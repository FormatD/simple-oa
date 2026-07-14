<template>
  <div class="employee-detail-page">
    <el-card v-loading="loading">
      <template #header>
        <div class="page-header">
          <span class="title">
            <el-button text @click="$router.push('/hr/employees')">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            员工详情 - {{ employee?.employee_no }}
          </span>
          <div>
            <el-tag :type="statusType(employee?.status)" size="large">
              {{ statusLabel(employee?.status) }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border v-if="employee">
        <el-descriptions-item label="工号">{{ employee.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ employee.display_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ employee.email || "-" }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ employee.department_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="岗位">{{ employee.position_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="雇佣类型">{{ typeLabel(employee.employment_type) }}</el-descriptions-item>
        <el-descriptions-item label="入职日期">{{ employee.hire_date }}</el-descriptions-item>
        <el-descriptions-item label="工作地点">{{ employee.work_location || "-" }}</el-descriptions-item>
        <el-descriptions-item label="汇报上级">
          <el-button v-if="employee.reports_to" link type="primary" size="small">
            查看上级
          </el-button>
          <span v-else>无</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ employee.created_at }}</el-descriptions-item>
      </el-descriptions>

      <el-empty v-else-if="!loading" description="员工信息未找到" />
    </el-card>

    <!-- Contracts Section -->
    <el-card style="margin-top: 16px">
      <template #header>
        <div class="page-header">
          <span class="title">合同管理</span>
        </div>
      </template>
      <el-table :data="contracts" v-loading="contractsLoading" stripe style="width: 100%">
        <el-table-column prop="contract_type" label="合同类型" width="140">
          <template #default="{ row }">
            <el-tag size="small">{{ contractTypeLabel(row.contract_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120">
          <template #default="{ row }">{{ row.end_date || "无固定期限" }}</template>
        </el-table-column>
        <el-table-column prop="probation_months" label="试用期(月)" width="100" />
        <el-table-column prop="signing_date" label="签订日期" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import http from "@/api/client"
import type { APIResponse, EmployeeDetail } from "@/types/hr"

const route = useRoute()
const loading = ref(false)
const employee = ref<EmployeeDetail | null>(null)
const contracts = ref<any[]>([])
const contractsLoading = ref(false)

function statusType(s?: string) {
  const map: Record<string, string> = { active: "success", probation: "warning", resigned: "info", suspended: "danger" }
  return map[s || ""] || "info"
}

function statusLabel(s?: string) {
  const map: Record<string, string> = { active: "在职", probation: "试用期", resigned: "离职", suspended: "停职" }
  return map[s || ""] || s || "-"
}

function typeLabel(t: string) {
  const map: Record<string, string> = { full_time: "全职", part_time: "兼职", contract: "合同", intern: "实习" }
  return map[t] || t
}

function contractTypeLabel(t: string) {
  const map: Record<string, string> = { probation: "试用期", fixed: "固定期限", permanent: "无固定期限", project: "项目合同" }
  return map[t] || t
}

async function loadEmployee() {
  const empId = route.params.empId as string
  if (!empId) return
  loading.value = true
  try {
    const res = await http.get<APIResponse<EmployeeDetail>>(`/hr/employees/${empId}`)
    employee.value = res.data.data || null
  } catch {
    employee.value = null
  } finally {
    loading.value = false
  }
}

async function loadContracts() {
  const empId = route.params.empId as string
  if (!empId) return
  contractsLoading.value = true
  try {
    const res = await http.get<APIResponse<any[]>>(`/hr/employees/${empId}/contracts`)
    contracts.value = res.data.data || []
  } catch {
    contracts.value = []
  } finally {
    contractsLoading.value = false
  }
}

onMounted(() => {
  loadEmployee()
  loadContracts()
})
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  .title {
    font-size: 18px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
</style>
