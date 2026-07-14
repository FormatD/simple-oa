<template>
  <div class="attendance-page">
    <el-row :gutter="16">
      <!-- Check-in/out Card -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span class="title">今日打卡</span>
          </template>
          <div class="check-in-card">
            <div class="time-display">{{ currentTime }}</div>
            <div class="date-display">{{ todayDate }}</div>
            <div class="status-info">
              <el-tag v-if="todayRecord?.check_in_time && todayRecord?.check_out_time" type="success" size="large">
                已完成打卡
              </el-tag>
              <el-tag v-else-if="todayRecord?.check_in_time" type="warning" size="large">
                已签到，待签退
              </el-tag>
              <el-tag v-else type="info" size="large">
                未打卡
              </el-tag>
            </div>
            <div v-if="todayRecord?.check_in_time" class="time-info">
              签到: {{ formatTime(todayRecord.check_in_time) }}
            </div>
            <div v-if="todayRecord?.check_out_time" class="time-info">
              签退: {{ formatTime(todayRecord.check_out_time) }}
            </div>
            <el-divider />
            <el-button
              :type="todayRecord?.check_in_time ? 'warning' : 'primary'"
              size="large"
              :loading="checkingIn"
              :disabled="!!(todayRecord?.check_in_time && todayRecord?.check_out_time)"
              @click="handleCheck"
              style="width: 100%"
            >
              {{ todayRecord?.check_in_time ? (todayRecord?.check_out_time ? '已完成' : '签退') : '签到' }}
            </el-button>
            <div v-if="locationStatus" class="location-info">
              <el-icon><Location /></el-icon> {{ locationStatus }}
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Summary Card -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <span class="title">考勤概况</span>
          </template>
          <el-row :gutter="12">
            <el-col :span="6">
              <el-statistic title="出勤天数" :value="summary?.present_days || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="迟到" :value="summary?.late_days || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="早退" :value="summary?.early_leave_days || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="加班(小时)" :value="summary?.overtime_hours || 0" :precision="1" />
            </el-col>
          </el-row>
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>
            <div class="page-header">
              <span class="title">考勤记录</span>
              <el-radio-group v-model="statusFilter" size="small" @change="loadRecords">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button value="present">正常</el-radio-button>
                <el-radio-button value="late">迟到</el-radio-button>
                <el-radio-button value="absent">缺勤</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="records" v-loading="recordsLoading" stripe style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column label="签到" width="160">
              <template #default="{ row }">
                {{ formatTime(row.check_in_time) || "-" }}
              </template>
            </el-table-column>
            <el-table-column label="签退" width="160">
              <template #default="{ row }">
                {{ formatTime(row.check_out_time) || "-" }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'present' ? 'success' : row.status === 'late' ? 'warning' : 'danger'" size="small">
                  {{ row.status === 'present' ? '正常' : row.status === 'late' ? '迟到' : row.status === 'absent' ? '缺勤' : row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="overtime_hours" label="加班(小时)" width="100">
              <template #default="{ row }">{{ row.overtime_hours || "-" }}</template>
            </el-table-column>
            <el-table-column prop="notes" label="备注" min-width="150" />
          </el-table>
          <div class="pagination-wrapper" v-if="totalRecords > pageSize">
            <el-pagination
              v-model:current-page="recordsPage"
              v-model:page-size="recordsPageSize"
              :total="totalRecords"
              :page-sizes="[10, 20, 50]"
              layout="sizes, prev, pager, next"
              @change="loadRecords"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, AttendanceRecord, AttendanceSummary } from "@/types/hr"

const currentTime = ref("")
const todayDate = ref("")
const timer = ref<ReturnType<typeof setInterval>>()
const todayRecord = ref<AttendanceRecord | null>(null)
const checkingIn = ref(false)
const locationStatus = ref("")
const summary = ref<AttendanceSummary | null>(null)
const records = ref<AttendanceRecord[]>([])
const recordsLoading = ref(false)
const statusFilter = ref("")
const recordsPage = ref(1)
const recordsPageSize = ref(10)
const totalRecords = ref(0)

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString("zh-CN", { hour12: false })
  todayDate.value = now.toLocaleDateString("zh-CN", {
    year: "numeric", month: "long", day: "numeric", weekday: "long",
  })
}

function formatTime(ts?: string | null) {
  if (!ts) return null
  const d = new Date(ts)
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
}

function getLocation(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation not supported"))
      return
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
    })
  })
}

async function handleCheck() {
  checkingIn.value = true
  try {
    const now = new Date()
    const timestamp = now.toISOString()
    let location = null
    try {
      const pos = await getLocation()
      location = { lat: pos.coords.latitude, lng: pos.coords.longitude }
      locationStatus.value = `${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`
    } catch {
      locationStatus.value = "无法获取位置（可选，仍可打卡）"
    }

    if (!todayRecord.value?.check_in_time) {
      await http.post("/hr/attendance/check-in", { timestamp, location })
      ElMessage.success("签到成功")
    } else {
      await http.post("/hr/attendance/check-out", { timestamp, location })
      ElMessage.success("签退成功")
    }
    await loadTodayRecord()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || "打卡失败")
  } finally {
    checkingIn.value = false
  }
}

async function loadTodayRecord() {
  const today = new Date().toISOString().split("T")[0]
  try {
    const res = await http.get<APIResponse<AttendanceRecord[]>>("/hr/attendance/my", {
      params: { date_from: today, date_to: today, page_size: 1 },
    })
    todayRecord.value = res.data?.data?.[0] || null
  } catch {
    todayRecord.value = null
  }
}

async function loadSummary() {
  try {
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split("T")[0]
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split("T")[0]
    const res = await http.get<APIResponse<AttendanceSummary>>("/hr/attendance/summary", {
      params: { date_from: firstDay, date_to: lastDay },
    })
    summary.value = res.data.data || null
  } catch {
    summary.value = null
  }
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const params: Record<string, any> = { page: recordsPage.value, page_size: recordsPageSize.value }
    if (statusFilter.value) params.status = statusFilter.value
    const res = await http.get<APIResponse<{ data: AttendanceRecord[]; pagination: any }>>("/hr/attendance/my", { params })
    records.value = res.data.data?.data || []
    totalRecords.value = res.data.data?.pagination?.total || 0
  } catch {
    records.value = []
  } finally {
    recordsLoading.value = false
  }
}

onMounted(() => {
  updateTime()
  timer.value = setInterval(updateTime, 1000)
  loadTodayRecord()
  loadSummary()
  loadRecords()
})

onUnmounted(() => {
  if (timer.value) clearInterval(timer.value)
})
</script>

<style scoped lang="scss">
.title { font-size: 16px; font-weight: 600; }

.check-in-card {
  text-align: center;

  .time-display {
    font-size: 36px;
    font-weight: 700;
    color: #303133;
    font-variant-numeric: tabular-nums;
  }
  .date-display {
    font-size: 14px;
    color: #909399;
    margin-top: 4px;
  }
  .status-info {
    margin: 16px 0;
  }
  .time-info {
    font-size: 13px;
    color: #606266;
    margin: 4px 0;
  }
  .location-info {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
