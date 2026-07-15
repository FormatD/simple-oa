<template>
  <div class="plan-list-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">培训计划管理</span>
          <el-button type="primary" @click="showCreate = true">
            <el-icon><Plus /></el-icon>新建计划
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 130px">
            <el-option label="草稿" value="draft" />
            <el-option label="报名中" value="open" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至"
            start-placeholder="开始日期" end-placeholder="结束日期" style="width: 240px" />
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="filters.search" placeholder="计划名称/地点" clearable style="width: 200px"
            @keyup.enter="loadPlans" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadPlans">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="plans" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="title" label="计划名称" min-width="160" />
        <el-table-column prop="course_title" label="关联课程" width="160" />
        <el-table-column prop="start_date" label="开始日期" width="110" />
        <el-table-column prop="end_date" label="结束日期" width="110" />
        <el-table-column prop="location" label="地点" width="140" />
        <el-table-column prop="instructor_name" label="讲师" width="120" />
        <el-table-column label="报名人数" width="100" align="center">
          <template #default="{ row }">
            {{ row.registered_count }}{{ row.max_participants ? `/${row.max_participants}` : '' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editPlan(row)">编辑</el-button>
            <el-button v-if="row.status === 'draft'" link type="primary" size="small" @click="publishPlan(row)">发布</el-button>
            <el-button v-if="row.status === 'open'" link type="warning" size="small" @click="cancelPlan(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadPlans" />
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑计划' : '新建计划'" width="700px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="关联课程" prop="course_id">
          <el-select v-model="form.course_id" filterable style="width: 100%" @change="onCourseChange">
            <el-option v-for="c in courseOptions" :key="c.id" :label="c.title" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划名称" prop="title">
          <el-input v-model="form.title" placeholder="继承课程名称或自行输入" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始日期" prop="start_date">
              <el-date-picker v-model="form.start_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期" prop="end_date">
              <el-date-picker v-model="form.end_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-time-picker v-model="form.start_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-time-picker v-model="form.end_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="培训地点">
          <el-input v-model="form.location" placeholder="培训教室/会议室/线上链接" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="讲师">
              <el-select v-model="form.instructor_id" filterable clearable style="width: 100%">
                <el-option v-for="i in instructorOptions" :key="i.id" :label="i.name" :value="i.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="人数上限">
              <el-input-number v-model="form.max_participants" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注说明">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, PaginatedResponse, TrainingPlan } from "@/types/training"
import type { TrainingCourse } from "@/types/training"

const loading = ref(false)
const plans = ref<TrainingPlan[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filters = reactive({ status: "", search: "" })
const dateRange = ref<[Date, Date] | null>(null)
const showDialog = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingId = ref("")
const formRef = ref()

const courseOptions = ref<TrainingCourse[]>([])
const instructorOptions = ref<any[]>([])

const form = reactive({
  course_id: "",
  title: "",
  start_date: null as any,
  end_date: null as any,
  start_time: null as any,
  end_time: null as any,
  location: "",
  instructor_id: null as any,
  max_participants: null as number | null,
  notes: "",
})

const rules = {
  course_id: [{ required: true, message: "请选择关联课程", trigger: "change" }],
  title: [{ required: true, message: "请输入计划名称", trigger: "blur" }],
  start_date: [{ required: true, message: "请选择开始日期", trigger: "change" }],
  end_date: [{ required: true, message: "请选择结束日期", trigger: "change" }],
}

function statusType(s: string) {
  const map: Record<string, string> = {
    draft: "info", open: "success", in_progress: "warning", completed: "", cancelled: "danger",
  }
  return map[s] || "info"
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    draft: "草稿", open: "报名中", in_progress: "进行中", completed: "已完成", cancelled: "已取消",
  }
  return map[s] || s
}

async function loadCourses() {
  try {
    const res = await http.get<APIResponse<PaginatedResponse<TrainingCourse>>>("/hr/training/courses", { params: { page_size: 200 } })
    courseOptions.value = res.data.data?.data || []
  } catch { }
}

async function loadInstructors() {
  try {
    const res = await http.get<APIResponse<PaginatedResponse<any>>>("/hr/training/instructors", { params: { page_size: 200 } })
    instructorOptions.value = res.data.data?.data || []
  } catch { }
}

function onCourseChange(courseId: string) {
  const course = courseOptions.value.find(c => c.id === courseId)
  if (course && !isEdit.value) {
    form.title = course.title
    form.max_participants = course.max_participants
  }
}

async function loadPlans() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    if (dateRange.value) {
      params.date_from = dateRange.value[0].toISOString().split("T")[0]
      params.date_to = dateRange.value[1].toISOString().split("T")[0]
    }
    const res = await http.get<APIResponse<PaginatedResponse<TrainingPlan>>>("/hr/training/plans", { params })
    if (res.data.data) {
      plans.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch { ElMessage.error("加载计划列表失败") }
  finally { loading.value = false }
}

function resetFilters() {
  filters.status = ""; filters.search = ""; dateRange.value = null
  page.value = 1; loadPlans()
}

function resetForm() {
  form.course_id = ""; form.title = ""; form.start_date = null; form.end_date = null
  form.start_time = null; form.end_time = null; form.location = ""
  form.instructor_id = null; form.max_participants = null; form.notes = ""
}

function editPlan(row: TrainingPlan) {
  isEdit.value = true; editingId.value = row.id
  form.course_id = row.course_id; form.title = row.title
  form.start_date = row.start_date ? new Date(row.start_date) : null
  form.end_date = row.end_date ? new Date(row.end_date) : null
  form.start_time = row.start_time || null; form.end_time = row.end_time || null
  form.location = row.location || ""; form.instructor_id = row.instructor_id || null
  form.max_participants = row.max_participants; form.notes = row.notes || ""
  showDialog.value = true
}

async function publishPlan(row: TrainingPlan) {
  try {
    await http.put(`/hr/training/plans/${row.id}`, { status: "open" })
    ElMessage.success("计划已发布")
    loadPlans()
  } catch { ElMessage.error("发布失败") }
}

async function cancelPlan(row: TrainingPlan) {
  try {
    await http.put(`/hr/training/plans/${row.id}`, { status: "cancelled" })
    ElMessage.success("计划已取消")
    loadPlans()
  } catch { ElMessage.error("取消失败") }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      ...form,
      start_date: form.start_date instanceof Date ? form.start_date.toISOString().split("T")[0] : form.start_date,
      end_date: form.end_date instanceof Date ? form.end_date.toISOString().split("T")[0] : form.end_date,
    }
    if (isEdit.value) {
      await http.put(`/hr/training/plans/${editingId.value}`, payload)
      ElMessage.success("计划更新成功")
    } else {
      await http.post("/hr/training/plans", payload)
      ElMessage.success("计划创建成功")
    }
    showDialog.value = false; resetForm(); loadPlans()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "保存失败") }
  finally { saving.value = false }
}

onMounted(() => { loadPlans(); loadCourses(); loadInstructors() })
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
