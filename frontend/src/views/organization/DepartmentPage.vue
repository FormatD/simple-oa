<template>
  <div class="department-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>部门树</span>
              <el-button type="primary" size="small" icon="Plus" @click="showCreate = true">
                添加部门
              </el-button>
            </div>
          </template>

          <el-tree
            :data="departmentTree"
            :props="{ label: 'name', children: 'children' }"
            :highlight-current="true"
            node-key="id"
            :default-expand-all="true"
            @node-click="handleNodeClick"
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <el-icon><FolderOpened /></el-icon>
                <span>{{ data.name }}</span>
                <span class="member-count" v-if="data.member_count">
                  ({{ data.member_count }})
                </span>
              </span>
            </template>
          </el-tree>

          <el-empty v-if="!loading && departmentTree.length === 0" description="暂无部门" />
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <span>{{ selectedDept ? selectedDept.name : "部门详情" }}</span>
          </template>

          <div v-if="selectedDept">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="部门名称" :span="2">
                {{ selectedDept.name }}
              </el-descriptions-item>
              <el-descriptions-item label="排序">
                {{ selectedDept.sort_order }}
              </el-descriptions-item>
              <el-descriptions-item label="成员数">
                {{ selectedDept.member_count }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="dept-actions" style="margin-top: 20px">
              <el-button size="small" icon="Edit">编辑</el-button>
              <el-button size="small" type="danger" icon="Delete">删除</el-button>
            </div>
          </div>

          <el-empty v-else description="请选择一个部门" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="创建部门" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-tree-select
            v-model="form.parent_id"
            :data="departmentTree"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            placeholder="选择上级部门（可选）"
            clearable
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue"
import { ElMessage, type FormInstance, type FormRules } from "element-plus"
import http from "@/api/client"
import type { APIResponse, Department, Organization } from "@/types/auth"

const loading = ref(false)
const creating = ref(false)
const showCreate = ref(false)
const formRef = ref<FormInstance>()
const departmentTree = ref<Department[]>([])
const selectedDept = ref<Department | null>(null)

// Default org ID — will be selected from user's orgs
const orgId = ref<string>("")

const form = reactive({
  name: "",
  parent_id: null as string | null,
})

const rules: FormRules = {
  name: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
}

async function fetchDepartments() {
  if (!orgId.value) return
  loading.value = true
  try {
    const res = await http.get<APIResponse<Department[]>>(
      `/organizations/${orgId.value}/departments`
    )
    departmentTree.value = res.data.data || []
  } catch {
    ElMessage.error("加载部门失败")
  } finally {
    loading.value = false
  }
}

async function fetchOrgId() {
  try {
    const res = await http.get<APIResponse<Organization[]>>("/organizations")
    const orgs = res.data.data || []
    if (orgs.length > 0) {
      orgId.value = orgs[0].id
      await fetchDepartments()
    }
  } catch {
    // no orgs yet
  }
}

function handleNodeClick(data: Department) {
  selectedDept.value = data
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await http.post(`/organizations/${orgId.value}/departments`, {
      name: form.name,
      parent_id: form.parent_id,
    })
    ElMessage.success("部门创建成功")
    showCreate.value = false
    form.name = ""
    form.parent_id = null
    await fetchDepartments()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || "创建失败")
  } finally {
    creating.value = false
  }
}

onMounted(fetchOrgId)
</script>

<style scoped lang="scss">
.department-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 6px;
    .member-count {
      color: #909399;
      font-size: 12px;
    }
  }

  .dept-actions {
    display: flex;
    gap: 8px;
  }
}
</style>
