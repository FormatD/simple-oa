<template>
  <div class="evaluation-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span class="title">培训效果评估</span>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="培训计划">
          <el-select v-model="filters.plan_id" filterable clearable placeholder="选择培训计划" style="width: 300px">
            <el-option v-for="p in planOptions" :key="p.id" :label="p.title" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadEvaluations">查询</el-button>
          <el-button @click="filters.plan_id = ''; loadEvaluations()">重置</el-button>
        </el-form-item>
      </el-form>

      <div v-if="!filters.plan_id" class="empty-hint">
        <el-empty description="请选择一个培训计划查看评估结果" />
      </div>

      <template v-else>
        <!-- Rating Summary -->
        <el-row :gutter="16" class="summary-cards">
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card">
              <div class="summary-value" :style="{ color: ratingColor(avgRatings.overall) }">{{ avgRatings.overall || '-' }}</div>
              <div class="summary-label">综合评分</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card">
              <div class="summary-value" :style="{ color: ratingColor(avgRatings.content) }">{{ avgRatings.content || '-' }}</div>
              <div class="summary-label">内容评分</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card">
              <div class="summary-value" :style="{ color: ratingColor(avgRatings.instructor) }">{{ avgRatings.instructor || '-' }}</div>
              <div class="summary-label">讲师评分</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="summary-card">
              <div class="summary-value" :style="{ color: ratingColor(avgRatings.practical) }">{{ avgRatings.practical || '-' }}</div>
              <div class="summary-label">实用性评分</div>
            </el-card>
          </el-col>
        </el-row>

        <el-table :data="evaluations" v-loading="loading" stripe style="width: 100%; margin-top: 16px">
          <el-table-column prop="employee_name" label="员工" width="120" />
          <el-table-column label="综合评分" width="110" align="center">
            <template #default="{ row }">
              <el-rate v-model="row.overall_rating" disabled :max="5" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="内容评分" width="100" align="center">
            <template #default="{ row }">{{ row.content_rating || '-' }} / 5</template>
          </el-table-column>
          <el-table-column label="讲师评分" width="100" align="center">
            <template #default="{ row }">{{ row.instructor_rating || '-' }} / 5</template>
          </el-table-column>
          <el-table-column label="实用性评分" width="100" align="center">
            <template #default="{ row }">{{ row.practical_rating || '-' }} / 5</template>
          </el-table-column>
          <el-table-column prop="comment" label="评价内容" min-width="200" show-overflow-tooltip />
          <el-table-column prop="submitted_at" label="提交时间" width="170" />
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse, TrainingEvaluation, TrainingPlan } from "@/types/training"

const loading = ref(false)
const evaluations = ref<TrainingEvaluation[]>([])
const planOptions = ref<TrainingPlan[]>([])
const filters = reactive({ plan_id: "" })

const avgRatings = computed(() => {
  const items = evaluations.value
  if (!items.length) return { overall: null, content: null, instructor: null, practical: null }
  const sum = (key: keyof TrainingEvaluation) => items.reduce((a, b) => a + (Number(b[key]) || 0), 0)
  return {
    overall: (sum("overall_rating") / items.length).toFixed(1),
    content: (sum("content_rating") / items.filter(i => i.content_rating).length).toFixed(1),
    instructor: (sum("instructor_rating") / items.filter(i => i.instructor_rating).length).toFixed(1),
    practical: (sum("practical_rating") / items.filter(i => i.practical_rating).length).toFixed(1),
  }
})

function ratingColor(val: string | null) {
  if (!val) return "#999"
  const n = parseFloat(val)
  if (n >= 4) return "#67C23A"
  if (n >= 3) return "#E6A23C"
  return "#F56C6C"
}

async function loadPlans() {
  try {
    const res = await http.get<APIResponse<any>>("/hr/training/plans", { params: { page_size: 200 } })
    planOptions.value = res.data.data?.data || []
  } catch { }
}

async function loadEvaluations() {
  if (!filters.plan_id) return
  loading.value = true
  try {
    const res = await http.get<APIResponse<TrainingEvaluation[]>>("/hr/training/evaluations", {
      params: { plan_id: filters.plan_id }
    })
    evaluations.value = res.data.data || []
  } catch { ElMessage.error("加载评估数据失败") }
  finally { loading.value = false }
}

onMounted(loadPlans)
watch(() => filters.plan_id, (val) => { if (val) loadEvaluations() })
</script>

<style scoped lang="scss">
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  .title { font-size: 18px; font-weight: 600; }
}
.filter-bar { margin-bottom: 12px; }
.empty-hint { padding: 60px 0; }
.summary-cards { margin-bottom: 8px; }
.summary-card { text-align: center; padding: 8px 0;
  .summary-value { font-size: 32px; font-weight: 700; }
  .summary-label { font-size: 14px; color: #909399; margin-top: 4px; }
}
</style>
