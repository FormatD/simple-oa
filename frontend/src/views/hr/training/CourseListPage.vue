<template>
  <div class="course-list-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">培训课程管理</span>
          <el-button type="primary" @click="showCreate = true">
            <el-icon><Plus /></el-icon>新建课程
          </el-button>
        </div>
      </template>

      <!-- Filters -->
      <el-form :inline="true" class="filter-bar">
        <el-form-item label="分类">
          <el-select v-model="filters.category" clearable placeholder="全部分类" style="width: 140px">
            <el-option label="通用培训" value="general" />
            <el-option label="技能培训" value="skill" />
            <el-option label="安全培训" value="safety" />
            <el-option label="管理培训" value="management" />
            <el-option label="新员工入职" value="onboarding" />
            <el-option label="合规培训" value="compliance" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 120px">
            <el-option label="启用" value="active" />
            <el-option label="归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="filters.search" placeholder="课程名称" clearable style="width: 200px"
            @keyup.enter="loadCourses" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadCourses">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- Table -->
      <el-table :data="courses" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="title" label="课程名称" min-width="180" />
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_hours" label="时长(小时)" width="100" align="center" />
        <el-table-column prop="max_participants" label="人数上限" width="100" align="center" />
        <el-table-column prop="credits" label="学分" width="80" align="center" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewCourse(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="editCourse(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '归档' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadCourses" />
      </div>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑课程' : '新建课程'" width="650px" :close-on-click-modal="false">
      <el-form :model="form" label-width="110px" :rules="rules" ref="formRef">
        <el-form-item label="课程名称" prop="title">
          <el-input v-model="form.title" placeholder="请输入课程名称" />
        </el-form-item>
        <el-form-item label="课程分类" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="通用培训" value="general" />
            <el-option label="技能培训" value="skill" />
            <el-option label="安全培训" value="safety" />
            <el-option label="管理培训" value="management" />
            <el-option label="新员工入职" value="onboarding" />
            <el-option label="合规培训" value="compliance" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="课程简介和内容说明" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="时长(小时)">
              <el-input-number v-model="form.duration_hours" :min="0" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="人数上限">
              <el-input-number v-model="form.max_participants" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学分">
              <el-input-number v-model="form.credits" :min="0" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- Course Detail Dialog -->
    <el-dialog v-model="showDetail" title="课程详情" width="700px">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="课程名称">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ categoryLabel(detail.category) }}</el-descriptions-item>
          <el-descriptions-item label="时长">{{ detail.duration_hours }} 小时</el-descriptions-item>
          <el-descriptions-item label="人数上限">{{ detail.max_participants ?? '不限' }}</el-descriptions-item>
          <el-descriptions-item label="学分">{{ detail.credits ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.status === 'active' ? 'success' : 'info'" size="small">
              {{ detail.status === 'active' ? '启用' : '归档' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detail.description || '暂无描述' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">培训计划</el-divider>
        <el-table :data="detail.plans || []" stripe size="small">
          <el-table-column prop="title" label="计划名称" />
          <el-table-column prop="start_date" label="开始日期" width="120" />
          <el-table-column prop="end_date" label="结束日期" width="120" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">{{ planStatusLabel(row.status) }}</template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">课件资料</el-divider>
        <el-table :data="detail.materials || []" stripe size="small">
          <el-table-column prop="name" label="资料名称" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="description" label="说明" />
        </el-table>
      </template>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import http from "@/api/client"
import type { APIResponse, PaginatedResponse, TrainingCourse } from "@/types/training"

const loading = ref(false)
const courses = ref<TrainingCourse[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filters = reactive({ category: "", status: "", search: "" })
const showDialog = ref(false)
const showDetail = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingId = ref("")
const detail = ref<any>(null)
const formRef = ref()

const form = reactive({
  title: "",
  category: "general",
  description: "",
  duration_hours: null as number | null,
  max_participants: null as number | null,
  credits: null as number | null,
})

const rules = {
  title: [{ required: true, message: "请输入课程名称", trigger: "blur" }],
  category: [{ required: true, message: "请选择课程分类", trigger: "change" }],
}

function categoryLabel(cat: string) {
  const map: Record<string, string> = {
    general: "通用培训", skill: "技能培训", safety: "安全培训",
    management: "管理培训", onboarding: "新员工入职", compliance: "合规培训",
  }
  return map[cat] || cat
}

function planStatusLabel(s: string) {
  const map: Record<string, string> = {
    draft: "草稿", open: "报名中", in_progress: "进行中", completed: "已完成", cancelled: "已取消",
  }
  return map[s] || s
}

async function loadCourses() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.category) params.category = filters.category
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    const res = await http.get<APIResponse<PaginatedResponse<TrainingCourse>>>("/hr/training/courses", { params })
    if (res.data.data) {
      courses.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch { ElMessage.error("加载课程列表失败") }
  finally { loading.value = false }
}

function resetFilters() {
  filters.category = ""; filters.status = ""; filters.search = ""
  page.value = 1; loadCourses()
}

function resetForm() {
  form.title = ""; form.category = "general"; form.description = ""
  form.duration_hours = null; form.max_participants = null; form.credits = null
}

function editCourse(row: TrainingCourse) {
  isEdit.value = true; editingId.value = row.id
  form.title = row.title; form.category = row.category
  form.description = row.description || ""
  form.duration_hours = row.duration_hours; form.max_participants = row.max_participants
  form.credits = row.credits
  showDialog.value = true
}

function viewCourse(row: TrainingCourse) {
  detail.value = null
  http.get<APIResponse<any>>(`/hr/training/courses/${row.id}`).then(res => {
    detail.value = res.data.data
    showDetail.value = true
  }).catch(() => ElMessage.error("加载课程详情失败"))
}

async function toggleStatus(row: TrainingCourse) {
  const newStatus = row.status === "active" ? "archived" : "active"
  try {
    await http.put(`/hr/training/courses/${row.id}`, { status: newStatus })
    ElMessage.success(newStatus === "archived" ? "课程已归档" : "课程已启用")
    loadCourses()
  } catch { ElMessage.error("操作失败") }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...form }
    if (isEdit.value) {
      await http.put(`/hr/training/courses/${editingId.value}`, payload)
      ElMessage.success("课程更新成功")
    } else {
      await http.post("/hr/training/courses", payload)
      ElMessage.success("课程创建成功")
    }
    showDialog.value = false; resetForm(); loadCourses()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "保存失败") }
  finally { saving.value = false }
}

onMounted(loadCourses)
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
