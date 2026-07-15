<template>
  <div class="registration-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">培训报名与签到</span>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px">
            <el-option label="已报名" value="registered" />
            <el-option label="已签到" value="attended" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="缺勤" value="absent" />
          </el-select>
        </el-form-item>
        <el-form-item label="培训计划">
          <el-select v-model="filters.plan_id" filterable clearable placeholder="选择培训计划" style="width: 260px">
            <el-option v-for="p in planOptions" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadRegistrations">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="registrations" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="employee_name" label="员工姓名" width="120" />
        <el-table-column prop="employee_no" label="工号" width="100" />
        <el-table-column prop="plan_title" label="培训计划" min-width="180" />
        <el-table-column label="报名状态" width="100">
          <template #default="{ row }">
            <el-tag :type="regStatusType(row.status)" size="small">{{ regStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="签到状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.attendance_status" :type="attStatusType(row.attendance_status)" size="small">
              {{ attStatusLabel(row.attendance_status) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="check_in_time" label="签到时间" width="170" />
        <el-table-column prop="check_out_time" label="签退时间" width="170" />
        <el-table-column prop="credits_earned" label="获得学分" width="90" align="center" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'registered'" link type="success" size="small"
              @click="checkIn(row)">签到</el-button>
            <el-button v-if="row.check_in_time && !row.check_out_time" link type="warning" size="small"
              @click="checkOut(row)">签退</el-button>
            <el-button link type="danger" size="small" @click="cancelRegistration(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadRegistrations" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, PaginatedResponse, TrainingRegistration, TrainingPlan } from "@/types/training"

const loading = ref(false)
const registrations = ref<TrainingRegistration[]>([])
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const filters = reactive({ status: "", plan_id: "" })
const planOptions = ref<TrainingPlan[]>([])

function regStatusType(s: string) {
  const map: Record<string, string> = { registered: "", attended: "success", completed: "", cancelled: "info", absent: "danger" }
  return map[s] || "info"
}
function regStatusLabel(s: string) {
  const map: Record<string, string> = { registered: "已报名", attended: "已签到", completed: "已完成", cancelled: "已取消", absent: "缺勤" }
  return map[s] || s
}
function attStatusType(s: string) {
  const map: Record<string, string> = { present: "success", late: "warning", absent: "danger", early_leave: "info" }
  return map[s] || "info"
}
function attStatusLabel(s: string) {
  const map: Record<string, string> = { present: "正常", late: "迟到", absent: "缺勤", early_leave: "早退" }
  return map[s] || s
}

async function loadPlans() {
  try {
    const res = await http.get<APIResponse<PaginatedResponse<TrainingPlan>>>("/hr/training/plans", { params: { page_size: 200 } })
    planOptions.value = res.data.data?.data || []
  } catch { }
}

async function loadRegistrations() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.plan_id) params.plan_id = filters.plan_id
    const res = await http.get<APIResponse<PaginatedResponse<TrainingRegistration>>>("/hr/training/registrations", { params })
    if (res.data.data) {
      registrations.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch { ElMessage.error("加载报名记录失败") }
  finally { loading.value = false }
}

function resetFilters() { filters.status = ""; filters.plan_id = ""; page.value = 1; loadRegistrations() }

async function checkIn(row: TrainingRegistration) {
  try {
    await http.post(`/hr/training/registrations/${row.id}/check-in`, {})
    ElMessage.success("签到成功")
    loadRegistrations()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "签到失败") }
}

async function checkOut(row: TrainingRegistration) {
  try {
    await http.post(`/hr/training/registrations/${row.id}/check-out`, {})
    ElMessage.success("签退成功")
    loadRegistrations()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "签退失败") }
}

async function cancelRegistration(row: TrainingRegistration) {
  try {
    await http.put(`/hr/training/registrations/${row.id}`, { status: "cancelled" })
    ElMessage.success("报名已取消")
    loadRegistrations()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "操作失败") }
}

onMounted(() => { loadRegistrations(); loadPlans() })
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
