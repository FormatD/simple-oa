<template>
  <div class="organization-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>组织管理</span>
          <el-button type="primary" size="small" icon="Plus" @click="showCreate = true">
            创建组织
          </el-button>
        </div>
      </template>

      <el-table :data="organizations" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="name" label="组织名称" />
        <el-table-column prop="slug" label="标识" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" type="primary" link>编辑</el-button>
            <el-button size="small" type="danger" link>删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && organizations.length === 0" description="暂无组织" />
    </el-card>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="创建组织" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="组织名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入组织名称" />
        </el-form-item>
        <el-form-item label="标识" prop="slug">
          <el-input v-model="form.slug" placeholder="英文标识，如 my-company" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="可选"
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
import type { APIResponse, Organization } from "@/types/auth"

const loading = ref(false)
const creating = ref(false)
const showCreate = ref(false)
const formRef = ref<FormInstance>()
const organizations = ref<Organization[]>([])

const form = reactive({
  name: "",
  slug: "",
  description: "",
})

const rules: FormRules = {
  name: [{ required: true, message: "请输入组织名称", trigger: "blur" }],
  slug: [
    { required: true, message: "请输入标识", trigger: "blur" },
    { pattern: /^[a-z0-9-]+$/, message: "仅支持小写字母、数字和连字符", trigger: "blur" },
  ],
}

async function fetchOrganizations() {
  loading.value = true
  try {
    const res = await http.get<APIResponse<Organization[]>>("/organizations")
    organizations.value = res.data.data || []
  } catch {
    ElMessage.error("加载组织列表失败")
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await http.post("/organizations", {
      name: form.name,
      slug: form.slug,
      description: form.description || undefined,
    })
    ElMessage.success("组织创建成功")
    showCreate.value = false
    form.name = ""
    form.slug = ""
    form.description = ""
    await fetchOrganizations()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || "创建失败")
  } finally {
    creating.value = false
  }
}

onMounted(fetchOrganizations)
</script>

<style scoped lang="scss">
.organization-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
