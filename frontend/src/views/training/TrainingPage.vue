<template>
  <div class="training-page">
    <h2 class="page-title">培训管理</h2>

    <div class="page-actions">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon> 新建课程
      </el-button>
    </div>

    <el-table :data="courses" v-loading="loading" border>
      <el-table-column prop="title" label="课程名称" min-width="180" />
      <el-table-column prop="instructor" label="讲师" width="120" />
      <el-table-column prop="category" label="类别" width="100" />
      <el-table-column prop="enrollment_count" label="报名人数" width="90" />
      <el-table-column prop="max_participants" label="上限" width="70" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag
            :type="row.status === 'published' ? 'success' : row.status === 'in_progress' ? 'primary' : 'info'"
            size="small"
          >
            {{ { draft: "草稿", published: "已发布", in_progress: "进行中", completed: "已完成" }[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewEnrollments(row)">报名</el-button>
          <el-button size="small" @click="editCourse(row)">编辑</el-button>
          <el-popconfirm title="确定删除?" @confirm="deleteCourse(row.id)">
            <template #reference>
              <el-button size="small" type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreateDialog" :title="editingCourse ? '编辑课程' : '新建课程'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="课程名称" required>
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="讲师">
          <el-input v-model="form.instructor" />
        </el-form-item>
        <el-form-item label="类别">
          <el-input v-model="form.category" placeholder="如: 技术培训、安全培训" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="开始日期">
              <el-date-picker v-model="form.start_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束日期">
              <el-date-picker v-model="form.end_date" type="date" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="时长(小时)">
              <el-input-number v-model="form.duration_hours" :min="0" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="人数上限">
              <el-input-number v-model="form.max_participants" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="地点">
          <el-input v-model="form.location" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="进行中" value="in_progress" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <!-- Enrollment Dialog -->
    <el-dialog v-model="showEnrollDialog" title="报名管理" width="600px">
      <template v-if="selectedCourse">
        <p><strong>{{ selectedCourse.title }}</strong> - 已报名 {{ enrollments.length }} 人</p>

        <el-button size="small" type="primary" @click="showEnrollForm = !showEnrollForm">
          添加报名
        </el-button>

        <div v-if="showEnrollForm" class="enroll-form">
          <el-select
            v-model="newEnrollEmployeeIds"
            multiple
            filterable
            placeholder="选择员工"
            style="width: 100%"
          >
            <el-option
              v-for="emp in employeeOptions"
              :key="emp.id"
              :label="`${emp.display_name || emp.employee_no} - ${emp.employee_no}`"
              :value="emp.id"
            />
          </el-select>
          <el-button
            type="primary"
            size="small"
            :loading="enrolling"
            style="margin-top: 8px"
            @click="submitEnrollments"
          >
            确认报名
          </el-button>
        </div>

        <el-table :data="enrollments" size="small" class="enroll-table">
          <el-table-column prop="employee_name" label="姓名" width="120" />
          <el-table-column prop="employee_no" label="工号" width="100" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'completed' ? 'success' : row.status === 'attended' ? 'primary' : 'info'">
                {{ { enrolled: "已报名", attended: "已签到", completed: "已完成" }[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="成绩" width="70" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" link @click="markAttendance(row)">签到</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse } from "@/types/auth"
import type { TrainingCourse, TrainingCourseCreateRequest, TrainingEnrollment } from "@/types/training"
import type { EmployeeBasic } from "@/types/hr"

const courses = ref<TrainingCourse[]>([])
const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const editingCourse = ref<TrainingCourse | null>(null)
const showEnrollDialog = ref(false)
const selectedCourse = ref<TrainingCourse | null>(null)
const enrollments = ref<TrainingEnrollment[]>([])
const showEnrollForm = ref(false)
const newEnrollEmployeeIds = ref<string[]>([])
const employeeOptions = ref<EmployeeBasic[]>([])
const enrolling = ref(false)

const form = reactive<TrainingCourseCreateRequest & { status?: string }>({
  title: "",
  description: "",
  instructor: "",
  category: "",
  start_date: undefined,
  end_date: undefined,
  duration_hours: undefined,
  max_participants: undefined,
  location: "",
  status: "draft",
})

function resetForm() {
  Object.assign(form, {
    title: "",
    description: "",
    instructor: "",
    category: "",
    start_date: undefined,
    end_date: undefined,
    duration_hours: undefined,
    max_participants: undefined,
    location: "",
    status: "draft",
  })
  editingCourse.value = null
}

async function loadCourses() {
  loading.value = true
  try {
    const res = await http.get<APIResponse<{ data: TrainingCourse[] }>>("/training/courses?page_size=100")
    courses.value = res.data.data!.data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function saveCourse() {
  saving.value = true
  try {
    if (editingCourse.value) {
      await http.put(`/training/courses/${editingCourse.value.id}`, form)
      ElMessage.success("更新成功")
    } else {
      await http.post("/training/courses", form)
      ElMessage.success("创建成功")
    }
    showCreateDialog.value = false
    resetForm()
    loadCourses()
  } catch {
    ElMessage.error("保存失败")
  } finally {
    saving.value = false
  }
}

function editCourse(course: TrainingCourse) {
  editingCourse.value = course
  Object.assign(form, {
    title: course.title,
    description: course.description || "",
    instructor: course.instructor || "",
    category: course.category || "",
    start_date: course.start_date || undefined,
    end_date: course.end_date || undefined,
    duration_hours: course.duration_hours,
    max_participants: course.max_participants,
    location: course.location || "",
    status: course.status,
  })
  showCreateDialog.value = true
}

async function deleteCourse(id: string) {
  try {
    await http.delete(`/training/courses/${id}`)
    ElMessage.success("删除成功")
    loadCourses()
  } catch {
    ElMessage.error("删除失败")
  }
}

async function viewEnrollments(course: TrainingCourse) {
  selectedCourse.value = course
  showEnrollDialog.value = true
  showEnrollForm.value = false
  try {
    const res = await http.get<APIResponse<TrainingEnrollment[]>>(`/training/courses/${course.id}/enrollments`)
    enrollments.value = res.data.data!
  } catch {
    enrollments.value = []
  }
  // Load employee list for enrollment
  try {
    const empRes = await http.get<APIResponse<{ data: EmployeeBasic[] }>>("/hr/employees?page_size=200")
    employeeOptions.value = empRes.data.data!.data
  } catch {
    employeeOptions.value = []
  }
}

async function submitEnrollments() {
  if (!selectedCourse.value || newEnrollEmployeeIds.value.length === 0) return
  enrolling.value = true
  try {
    await http.post(`/training/courses/${selectedCourse.value.id}/enroll`, {
      employee_ids: newEnrollEmployeeIds.value,
    })
    ElMessage.success("报名成功")
    newEnrollEmployeeIds.value = []
    viewEnrollments(selectedCourse.value)
  } catch {
    ElMessage.error("报名失败")
  } finally {
    enrolling.value = false
  }
}

function markAttendance(enrollment: TrainingEnrollment) {
  // Quick toggle attendance
}

onMounted(() => {
  loadCourses()
})
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 20px;
  font-size: 22px;
  color: #303133;
}
.page-actions {
  margin-bottom: 16px;
}
.enroll-form {
  margin: 12px 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
.enroll-table {
  margin-top: 12px;
}
</style>
