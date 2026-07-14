<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>审计日志</h2>
    </div>

    <!-- Search Filters -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="操作者">
          <el-input v-model="filters.actor_id" placeholder="用户ID" style="width: 200px" clearable />
        </el-form-item>
        <el-form-item label="操作">
          <el-input v-model="filters.action" placeholder="操作类型" style="width: 180px" clearable />
        </el-form-item>
        <el-form-item label="资源类型">
          <el-select v-model="filters.resource_type" clearable placeholder="全部" style="width: 140px">
            <el-option label="员工" value="employee" />
            <el-option label="任务" value="task" />
            <el-option label="文档" value="wiki" />
            <el-option label="审批" value="leave" />
            <el-option label="考勤" value="attendance" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filters.date_from" type="datetime" style="width: 180px" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filters.date_to" type="datetime" style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Log Table -->
    <el-card shadow="never">
      <el-table :data="logs" v-loading="loading" style="width: 100%">
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="actor_name" label="操作者" width="120" />
        <el-table-column prop="action" label="操作" width="180">
          <template #default="{ row }">
            <el-tag size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="100" />
        <el-table-column prop="resource_name" label="资源" min-width="200" />
        <el-table-column label="详情" width="100">
          <template #default="{ row }">
            <el-button text size="small" type="primary" @click="showDetails(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          small
          @current-change="search"
        />
      </div>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="showDetail" title="日志详情" width="500px">
      <template v-if="selectedLog">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="ID">{{ selectedLog.id }}</el-descriptions-item>
          <el-descriptions-item label="操作者">{{ selectedLog.actor_name }} ({{ selectedLog.actor_email }})</el-descriptions-item>
          <el-descriptions-item label="操作类型">{{ selectedLog.action }}</el-descriptions-item>
          <el-descriptions-item label="资源类型">{{ selectedLog.resource_type }}</el-descriptions-item>
          <el-descriptions-item label="资源名称">{{ selectedLog.resource_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ selectedLog.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ formatDateTime(selectedLog.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="selectedLog.details" class="details-json">
          <h4>详细数据</h4>
          <pre>{{ JSON.stringify(selectedLog.details, null, 2) }}</pre>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import http from "@/api/client"
import type { AuditLogEntry } from "@/types/audit"

const logs = ref<AuditLogEntry[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const showDetail = ref(false)
const selectedLog = ref<AuditLogEntry | null>(null)

const filters = reactive({
  actor_id: "",
  action: "",
  resource_type: "",
  date_from: null as Date | null,
  date_to: null as Date | null,
})

async function search() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.actor_id) params.actor_id = filters.actor_id
    if (filters.action) params.action = filters.action
    if (filters.resource_type) params.resource_type = filters.resource_type
    if (filters.date_from) params.date_from = filters.date_from.toISOString()
    if (filters.date_to) params.date_to = filters.date_to.toISOString()

    const res = await http.get("/audit-logs", { params })
    if (res.data?.data) {
      logs.value = res.data.data
      total.value = res.data?.pagination?.total || 0
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.actor_id = ""
  filters.action = ""
  filters.resource_type = ""
  filters.date_from = null
  filters.date_to = null
  page.value = 1
  search()
}

function showDetails(log: AuditLogEntry) {
  selectedLog.value = log
  showDetail.value = true
}

function formatDateTime(d: string) {
  return d ? d.slice(0, 16).replace("T", " ") : ""
}

onMounted(() => {
  search()
})
</script>

<style scoped lang="scss">
.audit-page {
  .page-header {
    margin-bottom: 16px;
    h2 { margin: 0; font-size: 20px; }
  }

  .filter-card {
    margin-bottom: 16px;
    :deep(.el-card__body) {
      padding: 12px 16px;
    }
  }

  .pagination-wrap {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .details-json {
    margin-top: 16px;
    h4 { font-size: 14px; margin-bottom: 8px; }
    pre {
      background: #f5f7fa;
      padding: 12px;
      border-radius: 4px;
      font-size: 12px;
      max-height: 300px;
      overflow: auto;
    }
  }
}
</style>
