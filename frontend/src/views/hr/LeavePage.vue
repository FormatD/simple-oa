<template>
  <div class="leave-page">
    <!-- Balance Cards -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <span class="title">假期额度</span>
      </template>
      <el-row :gutter="12" v-if="balances.length > 0">
        <el-col :span="6" v-for="b in balances" :key="b.id">
          <el-card shadow="hover" class="balance-card">
            <div class="balance-name">{{ b.leave_type_name }}</div>
            <div class="balance-amount">{{ b.remaining_days }}<small>天</small></div>
            <el-progress
              :percentage="b.total_days > 0 ? Math.round((b.used_days / b.total_days) * 100) : 0"
              :stroke-width="6"
            />
            <div class="balance-detail">总额 {{ b.total_days }} / 已用 {{ b.used_days }}</div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-else description="暂无假期额度数据" />
    </el-card>

    <!-- Leave Requests -->
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">请假记录</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>提交请假
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="leaveStatusFilter" clearable placeholder="全部" style="width: 130px" @change="loadLeaveRequests">
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-table :data="leaveRequests" v-loading="leaveLoading" stripe style="width: 100%">
        <el-table-column prop="leave_type_name" label="请假类型" width="120" />
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column prop="total_days" label="天数" width="80" />
        <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="leaveStatusType(row.status)" size="small">
              {{ leaveStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审批人" width="120">
          <template #default="{ row }">{{ row.approver_name || "-" }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrapper" v-if="leaveTotal > leavePageSize">
        <el-pagination
          v-model:current-page="leavePage"
          v-model:page-size="leavePageSize"
          :total="leaveTotal"
          layout="sizes, prev, pager, next"
          @change="loadLeaveRequests"
        />
      </div>
    </el-card>

    <!-- Create Leave Request Dialog -->
    <el-dialog v-model="showCreateDialog" title="提交请假申请" width="500px" :close-on-click-modal="false">
      <el-form :model="leaveForm" label-width="100px" :rules="leaveFormRules" ref="leaveFormRef">
        <el-form-item label="请假类型" prop="leave_type_id">
          <el-select v-model="leaveForm.leave_type_id" style="width: 100%">
            <el-option v-for="lt in leaveTypes" :key="lt.id" :label="lt.name" :value="lt.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker v-model="leaveForm.start_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker v-model="leaveForm.end_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="原因" prop="reason">
          <el-input v-model="leaveForm.reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submittingLeave" @click="submitLeave">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, LeaveBalance, LeaveRequestData, LeaveTypeData } from "@/types/hr"

const balances = ref<LeaveBalance[]>([])
const leaveTypes = ref<LeaveTypeData[]>([])
const leaveRequests = ref<LeaveRequestData[]>([])
const leaveLoading = ref(false)
const leavePage = ref(1)
const leavePageSize = ref(10)
const leaveTotal = ref(0)
const leaveStatusFilter = ref("")

const showCreateDialog = ref(false)
const submittingLeave = ref(false)
const leaveFormRef = ref()
const leaveForm = ref({
  leave_type_id: "",
  start_date: "",
  end_date: "",
  reason: "",
})
const leaveFormRules = {
  leave_type_id: [{ required: true, message: "请选择请假类型", trigger: "change" }],
  start_date: [{ required: true, message: "请选择开始日期", trigger: "change" }],
  end_date: [{ required: true, message: "请选择结束日期", trigger: "change" }],
}

function leaveStatusType(s: string) {
  const map: Record<string, string> = { pending: "warning", approved: "success", rejected: "danger", cancelled: "info" }
  return map[s] || "info"
}
function leaveStatusLabel(s: string) {
  const map: Record<string, string> = { pending: "待审批", approved: "已通过", rejected: "已驳回", cancelled: "已取消" }
  return map[s] || s
}

async function loadBalances() {
  try {
    const res = await http.get<APIResponse<LeaveBalance[]>>("/hr/leave-balances")
    balances.value = res.data.data || []
  } catch {
    balances.value = []
  }
}

async function loadLeaveTypes() {
  try {
    const res = await http.get<APIResponse<LeaveTypeData[]>>("/hr/leave-types")
    leaveTypes.value = res.data.data || []
  } catch {
    leaveTypes.value = []
  }
}

async function loadLeaveRequests() {
  leaveLoading.value = true
  try {
    const params: Record<string, any> = { page: leavePage.value, page_size: leavePageSize.value }
    if (leaveStatusFilter.value) params.status = leaveStatusFilter.value
    const res = await http.get<APIResponse<{ data: LeaveRequestData[]; pagination: any }>>("/hr/leave-requests", { params })
    leaveRequests.value = res.data.data?.data || []
    leaveTotal.value = res.data.data?.pagination?.total || 0
  } catch {
    leaveRequests.value = []
  } finally {
    leaveLoading.value = false
  }
}

async function submitLeave() {
  const valid = await leaveFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submittingLeave.value = true
  try {
    const payload = {
      leave_type_id: leaveForm.value.leave_type_id,
      start_date: typeof leaveForm.value.start_date === "string" ? leaveForm.value.start_date : (leaveForm.value.start_date as any).toISOString().split("T")[0],
      end_date: typeof leaveForm.value.end_date === "string" ? leaveForm.value.end_date : (leaveForm.value.end_date as any).toISOString().split("T")[0],
      reason: leaveForm.value.reason,
    }
    await http.post("/hr/leave-requests", payload)
    ElMessage.success("请假申请已提交")
    showCreateDialog.value = false
    leaveForm.value = { leave_type_id: "", start_date: "", end_date: "", reason: "" }
    loadLeaveRequests()
    loadBalances()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || "提交失败")
  } finally {
    submittingLeave.value = false
  }
}

onMounted(() => {
  loadBalances()
  loadLeaveTypes()
  loadLeaveRequests()
})
</script>

<style scoped lang="scss">
.title { font-size: 16px; font-weight: 600; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  margin-bottom: 12px;
}

.balance-card {
  text-align: center;
  .balance-name { font-size: 14px; color: #606266; margin-bottom: 8px; }
  .balance-amount { font-size: 32px; font-weight: 700; color: #409eff; margin-bottom: 8px; }
  .balance-amount small { font-size: 14px; color: #909399; }
  .balance-detail { font-size: 12px; color: #909399; margin-top: 6px; }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
