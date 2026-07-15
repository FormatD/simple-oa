<template>
  <div class="report-page">
    <h2 class="page-title">报表中心</h2>

    <!-- Dashboard Stats -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_employees }}</div>
          <div class="stat-label">员工总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value green">{{ stats.active_employees }}</div>
          <div class="stat-label">在职员工</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value orange">{{ stats.pending_leave_count }}</div>
          <div class="stat-label">待审批请假</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value blue">{{ stats.today_attendance_rate }}%</div>
          <div class="stat-label">今日出勤率</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>部门人数统计</span>
          </template>
          <el-table :data="headcountData" size="small" v-loading="loadingHeadcount">
            <el-table-column prop="department" label="部门" min-width="120" />
            <el-table-column prop="headcount" label="总人数" width="70" />
            <el-table-column prop="active" label="在职" width="60" />
            <el-table-column prop="resigned" label="离职" width="60" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>请假统计</span>
          </template>
          <el-table :data="leaveSummary" size="small" v-loading="loadingLeave">
            <el-table-column prop="leave_type" label="类型" min-width="100" />
            <el-table-column prop="total_days" label="总天数" width="70" />
            <el-table-column prop="approved_days" label="已审批" width="70" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>任务概览</span>
          </template>
          <div class="task-stats">
            <div class="task-stat-item">
              <span class="label">待办任务</span>
              <span class="value">{{ stats.pending_tasks }}</span>
            </div>
            <div class="task-stat-item">
              <span class="label">已逾期</span>
              <span class="value danger">{{ stats.overdue_tasks }}</span>
            </div>
            <div class="task-stat-item">
              <span class="label">培训课程</span>
              <span class="value">{{ stats.training_count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="section-card">
      <template #header>
        <span>数据导出</span>
      </template>
      <el-form :inline="true" :model="exportForm" class="export-form">
        <el-form-item label="报表类型">
          <el-select v-model="exportForm.report_type" style="width: 160px">
            <el-option label="员工列表" value="employees" />
            <el-option label="部门人数" value="headcount" />
            <el-option label="培训课程" value="training" />
          </el-select>
        </el-form-item>
        <el-form-item label="格式">
          <el-select v-model="exportForm.format" style="width: 120px">
            <el-option label="Excel" value="excel" />
            <el-option label="PDF" value="pdf" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleExport" :loading="exporting">
            <el-icon><Download /></el-icon> 导出
          </el-button>
        </el-form-item>
      </el-form>
      <div v-if="exportResult" class="export-result">
        <el-alert type="success" show-icon :closable="false">
          <template #title>
            导出成功！{{ exportResult.data.length }} 条数据
          </template>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue"
import http from "@/api/client"
import { ElMessage } from "element-plus"
import type { APIResponse } from "@/types/auth"
import type { DashboardStats } from "@/types/imports"

interface HeadcountRow {
  department: string
  department_id: string
  headcount: number
  active: number
  resigned: number
}

interface LeaveSummaryRow {
  leave_type: string
  leave_type_id: string
  total_days: number
  approved_days: number
  pending_days: number
  employee_count: number
}

const stats = ref<DashboardStats>({
  total_employees: 0,
  active_employees: 0,
  department_count: 0,
  pending_leave_count: 0,
  today_attendance_rate: 0,
  pending_tasks: 0,
  overdue_tasks: 0,
  training_count: 0,
})
const headcountData = ref<HeadcountRow[]>([])
const leaveSummary = ref<LeaveSummaryRow[]>([])
const loadingHeadcount = ref(false)
const loadingLeave = ref(false)
const exporting = ref(false)
const exportResult = ref<any>(null)

const exportForm = reactive({
  report_type: "employees",
  format: "excel",
})

async function loadDashboard() {
  try {
    const res = await http.get<APIResponse<DashboardStats>>("/reports/dashboard")
    stats.value = res.data.data!
  } catch {
    // ignore
  }
}

async function loadHeadcount() {
  loadingHeadcount.value = true
  try {
    const res = await http.get<APIResponse<HeadcountRow[]>>("/reports/hr/headcount")
    headcountData.value = res.data.data!
  } catch {
    // ignore
  } finally {
    loadingHeadcount.value = false
  }
}

async function loadLeaveSummary() {
  loadingLeave.value = true
  try {
    const res = await http.get<APIResponse<LeaveSummaryRow[]>>("/reports/hr/leave-summary")
    leaveSummary.value = res.data.data!
  } catch {
    // ignore
  } finally {
    loadingLeave.value = false
  }
}

async function handleExport() {
  exporting.value = true
  exportResult.value = null
  try {
    const res = await http.post<APIResponse<any>>("/reports/export", exportForm)
    exportResult.value = res.data.data!
    ElMessage.success("导出成功")
  } catch {
    ElMessage.error("导出失败")
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadDashboard()
  loadHeadcount()
  loadLeaveSummary()
})
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 20px;
  font-size: 22px;
  color: #303133;
}
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  text-align: center;
  .stat-value {
    font-size: 32px;
    font-weight: 700;
    color: #409eff;
    line-height: 1.2;
    &.green { color: #67c23a; }
    &.orange { color: #e6a23c; }
    &.blue { color: #409eff; }
  }
  .stat-label {
    font-size: 14px;
    color: #909399;
    margin-top: 8px;
  }
}
.section-card {
  margin-bottom: 20px;
}
.task-stats {
  .task-stat-item {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
    .label { color: #606266; }
    .value { font-weight: 600; color: #303133; }
    .value.danger { color: #f56c6c; }
  }
}
.export-form {
  margin-bottom: 12px;
}
.export-result {
  margin-top: 12px;
}
</style>
