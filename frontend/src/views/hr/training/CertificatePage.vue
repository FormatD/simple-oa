<template>
  <div class="certificate-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">培训证书管理</span>
          <el-button type="primary" @click="showIssue = true">
            <el-icon><Plus /></el-icon>颁发证书
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 120px">
            <el-option label="有效" value="valid" />
            <el-option label="过期" value="expired" />
            <el-option label="吊销" value="revoked" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadCertificates">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="certificates" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="certificate_no" label="证书编号" width="180" />
        <el-table-column prop="employee_name" label="员工" width="120" />
        <el-table-column prop="course_title" label="培训课程" min-width="200" />
        <el-table-column prop="issued_date" label="颁发日期" width="120" />
        <el-table-column prop="expiry_date" label="过期日期" width="120" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'valid'" link type="danger" size="small"
              @click="revokeCertificate(row)">吊销</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadCertificates" />
      </div>
    </el-card>

    <el-dialog v-model="showIssue" title="颁发证书" width="550px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="员工">
          <el-select v-model="form.employee_id" filterable style="width: 100%">
            <el-option v-for="e in employeeOptions" :key="e.id" :label="`${e.display_name} (${e.employee_no})`" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="培训课程" prop="course_id">
          <el-select v-model="form.course_id" filterable style="width: 100%">
            <el-option v-for="c in courseOptions" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="颁发日期" prop="issued_date">
          <el-date-picker v-model="form.issued_date" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="过期日期">
          <el-date-picker v-model="form.expiry_date" type="date" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showIssue = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitIssue">确认颁发</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, PaginatedResponse, TrainingCertificate, TrainingCourse } from "@/types/training"

const loading = ref(false)
const certificates = ref<TrainingCertificate[]>([])
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const filters = reactive({ status: "" })
const showIssue = ref(false); const saving = ref(false); const formRef = ref()
const employeeOptions = ref<any[]>([])
const courseOptions = ref<TrainingCourse[]>([])

const form = reactive({
  employee_id: "", course_id: "", issued_date: null as any, expiry_date: null as any,
})

const rules = {
  course_id: [{ required: true, message: "请选择培训课程", trigger: "change" }],
  issued_date: [{ required: true, message: "请选择颁发日期", trigger: "change" }],
}

function statusType(s: string) { return s === "valid" ? "success" : s === "expired" ? "warning" : "danger" }
function statusLabel(s: string) { return s === "valid" ? "有效" : s === "expired" ? "过期" : "吊销" }

async function loadCertificates() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    const res = await http.get<APIResponse<PaginatedResponse<TrainingCertificate>>>("/hr/training/certificates", { params })
    if (res.data.data) {
      certificates.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch { ElMessage.error("加载证书列表失败") }
  finally { loading.value = false }
}

async function loadOptions() {
  try {
    const [empRes, courseRes] = await Promise.all([
      http.get("/hr/employees", { params: { page_size: 200 } }),
      http.get("/hr/training/courses", { params: { page_size: 200 } }),
    ])
    employeeOptions.value = empRes.data.data?.data || []
    courseOptions.value = courseRes.data.data?.data || []
  } catch { }
}

function resetFilters() { filters.status = ""; page.value = 1; loadCertificates() }

async function submitIssue() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      ...form,
      issued_date: form.issued_date instanceof Date ? form.issued_date.toISOString().split("T")[0] : form.issued_date,
      expiry_date: form.expiry_date instanceof Date ? form.expiry_date.toISOString().split("T")[0] : form.expiry_date,
    }
    await http.post("/hr/training/certificates", payload)
    ElMessage.success("证书颁发成功")
    showIssue.value = false; loadCertificates()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "颁发失败") }
  finally { saving.value = false }
}

async function revokeCertificate(row: TrainingCertificate) {
  try {
    await http.put(`/hr/training/certificates/${row.id}`, { status: "revoked" })
    ElMessage.success("证书已吊销")
    loadCertificates()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "操作失败") }
}

onMounted(() => { loadCertificates(); loadOptions() })
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
