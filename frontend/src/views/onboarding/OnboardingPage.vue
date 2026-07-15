<template>
  <div class="onboarding-page">
    <h2 class="page-title">入职/离职管理</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="入职管理" name="onboarding">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>新员工入职</span>
          </template>
          <el-form :model="onboardingForm" label-width="120px" class="onboarding-form">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="用户ID" required>
                  <el-input v-model="onboardingForm.user_id" placeholder="选择或输入用户ID" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="工号" required>
                  <el-input v-model="onboardingForm.employee_no" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="部门">
                  <el-input v-model="onboardingForm.department_id" placeholder="部门ID" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="岗位">
                  <el-input v-model="onboardingForm.position_id" placeholder="岗位ID" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="入职日期" required>
              <el-date-picker v-model="onboardingForm.hire_date" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="工作地点">
              <el-input v-model="onboardingForm.work_location" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="onboarding" @click="submitOnboarding">
                执行入职
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <h3>入职流程步骤</h3>
          <el-steps :active="onboardingStep" finish-status="success" class="onboarding-steps">
            <el-step title="创建档案" />
            <el-step title="分配部门" />
            <el-step title="开通账号" />
            <el-step title="分配福利" />
            <el-step title="入职完成" />
          </el-steps>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="离职管理" name="offboarding">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>离职处理</span>
          </template>

          <h3>离职员工列表</h3>
          <el-table :data="pendingOffboarding" v-loading="loadingOffboarding" border>
            <el-table-column prop="employee_no" label="工号" width="100" />
            <el-table-column prop="name" label="姓名" width="120" />
            <el-table-column prop="department" label="部门" min-width="120" />
            <el-table-column prop="resignation_date" label="离职日期" width="170" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-popconfirm title="确认完成离职? (权限和数据交接)" @confirm="completeOffboarding(row.id)">
                  <template #reference>
                    <el-button size="small" type="danger">完成离职</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse } from "@/types/auth"

const activeTab = ref("onboarding")
const onboarding = ref(false)
const onboardingStep = ref(0)
const pendingOffboarding = ref<any[]>([])
const loadingOffboarding = ref(false)

const onboardingForm = reactive({
  user_id: "",
  employee_no: "",
  department_id: "",
  position_id: "",
  hire_date: "",
  work_location: "",
})

async function submitOnboarding() {
  onboarding.value = true
  try {
    const res = await http.post<APIResponse<any>>("/onboarding/employees", onboardingForm)
    const data = res.data.data!
    ElMessage.success(`入职成功: ${data.employee_no}`)
    onboardingStep.value = 1
    // Process onboarding steps
    const steps = ["assign_department", "create_account", "assign_benefits", "complete"]
    for (let i = 0; i < steps.length; i++) {
      await http.post("/onboarding/process", {
        employee_id: data.employee_id,
        step: steps[i],
        department_id: onboardingForm.department_id || undefined,
      })
      onboardingStep.value = i + 2
    }
    ElMessage.success("入职流程完成")
  } catch {
    ElMessage.error("入职操作失败")
  } finally {
    onboarding.value = false
  }
}

async function completeOffboarding(empId: string) {
  try {
    await http.post(`/onboarding/offboarding/${empId}/complete`, {})
    ElMessage.success("离职流程已完成")
    loadPendingOffboarding()
  } catch {
    ElMessage.error("操作失败")
  }
}

async function loadPendingOffboarding() {
  loadingOffboarding.value = true
  try {
    const res = await http.get<APIResponse<any[]>>("/onboarding/pending")
    pendingOffboarding.value = res.data.data!
  } catch {
    pendingOffboarding.value = []
  } finally {
    loadingOffboarding.value = false
  }
}

onMounted(() => {
  loadPendingOffboarding()
})
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 20px;
  font-size: 22px;
  color: #303133;
}
.section-card {
  margin-bottom: 20px;
}
.onboarding-form {
  max-width: 600px;
}
.onboarding-steps {
  margin-top: 20px;
}
</style>
