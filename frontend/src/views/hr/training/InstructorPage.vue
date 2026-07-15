<template>
  <div class="instructor-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">讲师管理</span>
          <el-button type="primary" @click="showCreate = true">
            <el-icon><Plus /></el-icon>添加讲师
          </el-button>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="搜索">
          <el-input v-model="filters.search" placeholder="讲师姓名" clearable style="width: 200px"
            @keyup.enter="loadInstructors" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadInstructors">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="instructors" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="name" label="姓名" width="140" />
        <el-table-column prop="title" label="职称" width="160" />
        <el-table-column prop="expertise" label="专长" min-width="180" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_external ? 'warning' : ''" size="small">
              {{ row.is_external ? '外部' : '内部' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editInstructor(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadInstructors" />
      </div>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑讲师' : '添加讲师'" width="600px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="讲师姓名" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="职称">
              <el-input v-model="form.title" placeholder="职位/头衔" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="外部讲师">
              <el-switch v-model="form.is_external" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="专长领域">
          <el-input v-model="form.expertise" type="textarea" :rows="2" placeholder="教学专长领域" />
        </el-form-item>
        <el-form-item label="个人简介">
          <el-input v-model="form.bio" type="textarea" :rows="3" placeholder="讲师个人简介" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="电话">
              <el-input v-model="form.phone" placeholder="联系电话" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="form.email" placeholder="邮箱地址" />
            </el-form-item>
          </el-col>
        </el-row>
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
import type { APIResponse, PaginatedResponse, TrainingInstructor } from "@/types/training"

const loading = ref(false)
const instructors = ref<TrainingInstructor[]>([])
const page = ref(1); const pageSize = ref(20); const total = ref(0)
const filters = reactive({ search: "" })
const showDialog = ref(false); const isEdit = ref(false); const saving = ref(false)
const editingId = ref(""); const formRef = ref()

const form = reactive({
  name: "", title: "", expertise: "", bio: "", phone: "", email: "",
  is_external: false,
})

const rules = {
  name: [{ required: true, message: "请输入讲师姓名", trigger: "blur" }],
}

async function loadInstructors() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (filters.search) params.search = filters.search
    const res = await http.get<APIResponse<PaginatedResponse<TrainingInstructor>>>("/hr/training/instructors", { params })
    if (res.data.data) {
      instructors.value = res.data.data.data
      total.value = res.data.data.pagination.total
    }
  } catch { ElMessage.error("加载讲师列表失败") }
  finally { loading.value = false }
}

function resetFilters() { filters.search = ""; page.value = 1; loadInstructors() }

function resetForm() {
  form.name = ""; form.title = ""; form.expertise = ""; form.bio = ""
  form.phone = ""; form.email = ""; form.is_external = false
}

function editInstructor(row: TrainingInstructor) {
  isEdit.value = true; editingId.value = row.id
  form.name = row.name; form.title = row.title || ""; form.expertise = row.expertise || ""
  form.bio = row.bio || ""; form.phone = row.phone || ""; form.email = row.email || ""
  form.is_external = row.is_external
  showDialog.value = true
}

async function toggleStatus(row: TrainingInstructor) {
  const newStatus = row.status === "active" ? "inactive" : "active"
  try {
    await http.put(`/hr/training/instructors/${row.id}`, { status: newStatus })
    ElMessage.success(newStatus === "active" ? "讲师已启用" : "讲师已停用")
    loadInstructors()
  } catch { ElMessage.error("操作失败") }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await http.put(`/hr/training/instructors/${editingId.value}`, form)
      ElMessage.success("讲师更新成功")
    } else {
      await http.post("/hr/training/instructors", form)
      ElMessage.success("讲师添加成功")
    }
    showDialog.value = false; resetForm(); loadInstructors()
  } catch (err: any) { ElMessage.error(err.response?.data?.detail || "保存失败") }
  finally { saving.value = false }
}

onMounted(loadInstructors)
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
