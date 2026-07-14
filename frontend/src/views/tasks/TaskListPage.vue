<template>
  <div class="task-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h2>任务管理</h2>
      </div>
      <div class="header-right">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="kanban">
            <el-icon><Grid /></el-icon> 看板
          </el-radio-button>
          <el-radio-button value="list">
            <el-icon><List /></el-icon> 列表
          </el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 新建任务
        </el-button>
      </div>
    </div>

    <!-- Filter Bar -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" size="small">
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部" style="width: 140px">
            <el-option label="待办" value="todo" />
            <el-option label="进行中" value="in_progress" />
            <el-option label="审核" value="review" />
            <el-option label="完成" value="done" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="filters.priority" clearable placeholder="全部" style="width: 120px">
            <el-option label="紧急" value="urgent" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="filters.search" placeholder="任务标题" clearable style="width: 200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchTasks">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Kanban View -->
    <div v-if="viewMode === 'kanban'" class="kanban-board">
      <div class="kanban-columns">
        <div
          v-for="col in kanbanColumns"
          :key="col.status"
          class="kanban-column"
          @dragover.prevent
          @drop="onDrop($event, col.status)"
        >
          <div class="column-header">
            <h4>{{ columnLabels[col.status] }}</h4>
            <el-tag size="small" type="info">{{ col.tasks.length }}</el-tag>
          </div>
          <div class="column-body">
            <div
              v-for="task in col.tasks"
              :key="task.id"
              class="kanban-card"
              :draggable="true"
              @dragstart="onDragStart($event, task)"
              @click="openTaskDetail(task)"
            >
              <div class="card-title">{{ task.title }}</div>
              <div class="card-meta">
                <el-tag
                  :type="priorityType(task.priority)"
                  size="small"
                  effect="plain"
                >
                  {{ priorityLabel(task.priority) }}
                </el-tag>
                <span v-if="task.due_date" class="due-date">
                  {{ formatDate(task.due_date) }}
                </span>
              </div>
              <div v-if="task.assignee_name" class="card-assignee">
                <el-tag size="small" round>{{ task.assignee_name }}</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- List View -->
    <el-card v-else shadow="never">
      <el-table :data="taskStore.tasks" v-loading="taskStore.loading" @row-click="openTaskDetail" style="width: 100%">
        <el-table-column prop="title" label="任务标题" min-width="250">
          <template #default="{ row }">
            <div class="task-title-cell">
              <el-checkbox
                v-if="row.status !== 'done'"
                @click.stop
                @change="() => updateStatus(row, 'done')"
              />
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              {{ columnLabels[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" size="small" effect="plain">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="负责人" width="120" />
        <el-table-column prop="due_date" label="截止日期" width="120">
          <template #default="{ row }">
            {{ row.due_date ? formatDate(row.due_date) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text size="small" type="primary" @click.stop="openTaskDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap" v-if="taskStore.pagination.total > 0">
        <el-pagination
          v-model:current-page="filters.page"
          :page-size="filters.page_size"
          :total="taskStore.pagination.total"
          layout="total, prev, pager, next"
          small
          @current-change="searchTasks"
        />
      </div>
    </el-card>

    <!-- Create Task Dialog -->
    <el-dialog v-model="showCreateDialog" title="新建任务" width="600px">
      <el-form :model="createForm" label-width="80px" ref="createFormRef">
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="任务标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="createForm.assignee_id" placeholder="用户ID" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority">
            <el-option label="紧急" value="urgent" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="createForm.due_date" type="datetime" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- Task Detail Drawer -->
    <el-drawer v-model="showDetail" size="600px" title="任务详情">
      <template v-if="taskStore.currentTask">
        <div class="task-detail-header">
          <h3>{{ taskStore.currentTask.title }}</h3>
          <el-tag :type="statusType(taskStore.currentTask.status)" size="small">
            {{ columnLabels[taskStore.currentTask.status] }}
          </el-tag>
        </div>
        <el-descriptions :column="2" size="small" border class="detail-section">
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityType(taskStore.currentTask.priority)" size="small" effect="plain">
              {{ priorityLabel(taskStore.currentTask.priority) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="负责人">
            {{ taskStore.currentTask.assignee_name || '未分配' }}
          </el-descriptions-item>
          <el-descriptions-item label="创建者">
            {{ taskStore.currentTask.assigner_name }}
          </el-descriptions-item>
          <el-descriptions-item label="截止日期">
            {{ taskStore.currentTask.due_date ? formatDate(taskStore.currentTask.due_date) : '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- Status Actions -->
        <div class="detail-actions">
          <el-button
            v-if="taskStore.currentTask.status !== 'in_progress'"
            size="small"
            @click="updateStatus(taskStore.currentTask, 'in_progress')"
          >开始处理</el-button>
          <el-button
            v-if="taskStore.currentTask.status !== 'done'"
            size="small"
            type="success"
            @click="updateStatus(taskStore.currentTask, 'done')"
          >标记完成</el-button>
        </div>

        <!-- Description -->
        <div class="detail-section">
          <h4>描述</h4>
          <p>{{ taskStore.currentTask.description || '暂无描述' }}</p>
        </div>

        <!-- Subtasks -->
        <div class="detail-section">
          <h4>子任务</h4>
          <div class="subtask-list">
            <div v-for="st in taskStore.subtasks" :key="st.id" class="subtask-item">
              <el-checkbox v-model="st.is_done" @change="() => toggleSubtask(st)" />
              <span :class="{ 'is-done': st.is_done }">{{ st.title }}</span>
              <el-button text size="small" type="danger" @click="taskStore.deleteSubtask(taskStore.currentTask.id, st.id)">删除</el-button>
            </div>
          </div>
          <div class="subtask-add">
            <el-input v-model="newSubtask" placeholder="添加子任务" size="small" @keyup.enter="addSubtask">
              <template #append>
                <el-button @click="addSubtask">添加</el-button>
              </template>
            </el-input>
          </div>
        </div>

        <!-- Comments -->
        <div class="detail-section">
          <h4>评论</h4>
          <div class="comments-list">
            <div v-for="c in taskStore.comments" :key="c.id" class="comment-item">
              <div class="comment-header">
                <strong>{{ c.author_name }}</strong>
                <span class="comment-time">{{ formatDateTime(c.created_at) }}</span>
              </div>
              <p class="comment-content">{{ c.content }}</p>
            </div>
          </div>
          <div class="comment-add">
            <el-input
              v-model="newComment"
              type="textarea"
              :rows="2"
              placeholder="添加评论..."
              @keyup.enter.ctrl="addComment"
            />
            <el-button size="small" type="primary" @click="addComment" style="margin-top: 8px">发表</el-button>
          </div>
        </div>

        <!-- Activity Log -->
        <div class="detail-section">
          <h4>操作记录</h4>
          <el-timeline>
            <el-timeline-item
              v-for="a in taskStore.activities"
              :key="a.id"
              :timestamp="formatDateTime(a.created_at)"
              placement="top"
            >
              <p>{{ a.actor_name }} {{ actionLabel(a) }}</p>
            </el-timeline-item>
          </el-timeline>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from "vue"
import { useTaskStore } from "@/stores/taskStore"
import type { TaskData, KanbanColumn } from "@/types/task"
import { ElMessage } from "element-plus"

const taskStore = useTaskStore()

const viewMode = ref<"kanban" | "list">("kanban")
const showCreateDialog = ref(false)
const showDetail = ref(false)
const creating = ref(false)
const newSubtask = ref("")
const newComment = ref("")

const filters = reactive({
  status: "",
  priority: "",
  search: "",
  page: 1,
  page_size: 20,
})

const createForm = reactive({
  title: "",
  description: "",
  assignee_id: "",
  priority: "medium",
  due_date: null as Date | null,
})

const columnLabels: Record<string, string> = {
  todo: "待办",
  in_progress: "进行中",
  review: "审核",
  done: "完成",
}

const columnOrder = ["todo", "in_progress", "review", "done"]

const kanbanColumns = computed(() => {
  const cols: KanbanColumn[] = columnOrder.map((s) => ({ status: s, tasks: [] }))
  for (const col of taskStore.kanban) {
    const found = cols.find((c) => c.status === col.status)
    if (found) found.tasks = col.tasks
  }
  return cols
})

// Drag and drop state
let draggedTask: TaskData | null = null

function onDragStart(event: DragEvent, task: TaskData) {
  draggedTask = task
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("text/plain", task.id)
  }
}

async function onDrop(event: DragEvent, targetStatus: string) {
  if (!draggedTask) return
  const task = draggedTask
  draggedTask = null
  try {
    await taskStore.reorderTask(task.id, targetStatus, 0)
    await taskStore.fetchKanban()
    ElMessage.success("任务已移动")
  } catch {
    ElMessage.error("移动失败")
  }
}

// Priority helpers
function priorityType(p: string) {
  const map: Record<string, string> = { urgent: "danger", high: "warning", medium: "info", low: "info" }
  return map[p] || "info"
}

function priorityLabel(p: string) {
  const map: Record<string, string> = { urgent: "紧急", high: "高", medium: "中", low: "低" }
  return map[p] || p
}

function statusType(s: string) {
  const map: Record<string, string> = { todo: "info", in_progress: "warning", review: "", done: "success" }
  return map[s] || "info"
}

function formatDate(d: string) {
  return d ? d.slice(0, 10) : ""
}

function formatDateTime(d: string) {
  return d ? d.slice(0, 16).replace("T", " ") : ""
}

function actionLabel(a: any) {
  const map: Record<string, string> = {
    "task.created": "创建了任务",
    "task.updated": "更新了任务",
    "task.status_changed": `将状态从 ${a.old_value || '?'} 改为 ${a.new_value || '?'}`,
    "task.deleted": "删除了任务",
    "task.reordered": "移动了任务",
    "comment.created": "添加了评论",
    "subtask.created": "添加了子任务",
    "subtask.updated": "更新了子任务",
    "subtask.deleted": "删除了子任务",
  }
  return map[a.action] || a.action
}

async function searchTasks() {
  const params: Record<string, any> = { page: filters.page, page_size: filters.page_size }
  if (filters.status) params.status = filters.status
  if (filters.priority) params.priority = filters.priority
  if (filters.search) params.search = filters.search
  if (viewMode.value === "kanban") {
    await taskStore.fetchKanban()
  } else {
    await taskStore.fetchTasks(params)
  }
}

function resetFilters() {
  filters.status = ""
  filters.priority = ""
  filters.search = ""
  filters.page = 1
  searchTasks()
}

async function createTask() {
  if (!createForm.title) return
  creating.value = true
  try {
    const data: Record<string, any> = { title: createForm.title }
    if (createForm.description) data.description = createForm.description
    if (createForm.assignee_id) data.assignee_id = createForm.assignee_id
    if (createForm.priority) data.priority = createForm.priority
    if (createForm.due_date) data.due_date = createForm.due_date.toISOString()
    await taskStore.createTask(data)
    showCreateDialog.value = false
    createForm.title = ""
    createForm.description = ""
    createForm.assignee_id = ""
    createForm.priority = "medium"
    createForm.due_date = null
    ElMessage.success("任务创建成功")
    await searchTasks()
  } catch {
    ElMessage.error("创建失败")
  } finally {
    creating.value = false
  }
}

async function openTaskDetail(task: TaskData) {
  showDetail.value = true
  await taskStore.fetchTaskDetail(task.id)
  await taskStore.fetchSubtasks(task.id)
  await taskStore.fetchComments(task.id)
  await taskStore.fetchActivities(task.id)
}

async function updateStatus(task: TaskData, status: string) {
  await taskStore.updateTaskStatus(task.id, status)
  if (viewMode.value === "kanban") {
    await taskStore.fetchKanban()
  } else {
    await searchTasks()
  }
  if (showDetail.value) {
    await taskStore.fetchTaskDetail(task.id)
    await taskStore.fetchActivities(task.id)
  }
  ElMessage.success("状态已更新")
}

async function toggleSubtask(st: any) {
  await taskStore.updateSubtask(st.task_id, st.id, { is_done: st.is_done })
}

async function addSubtask() {
  if (!newSubtask.value || !taskStore.currentTask) return
  await taskStore.createSubtask(taskStore.currentTask.id, { title: newSubtask.value })
  newSubtask.value = ""
}

async function addComment() {
  if (!newComment.value || !taskStore.currentTask) return
  await taskStore.createComment(taskStore.currentTask.id, { content: newComment.value, mentions: [] })
  newComment.value = ""
  await taskStore.fetchComments(taskStore.currentTask.id)
}

onMounted(() => {
  searchTasks()
})
</script>

<style scoped lang="scss">
.task-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .header-left h2 {
      margin: 0;
      font-size: 20px;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .filter-card {
    margin-bottom: 16px;
    :deep(.el-card__body) {
      padding: 12px 16px;
    }
  }
}

.kanban-board {
  overflow-x: auto;
}

.kanban-columns {
  display: flex;
  gap: 16px;
  min-height: 400px;

  .kanban-column {
    flex: 1;
    min-width: 260px;
    background: #f0f2f5;
    border-radius: 8px;
    padding: 12px;

    .column-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      h4 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
      }
    }

    .column-body {
      min-height: 200px;
    }

    .kanban-card {
      background: #fff;
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 8px;
      cursor: pointer;
      transition: box-shadow 0.2s;
      border: 1px solid #e8e8e8;

      &:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }

      .card-title {
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 8px;
        line-height: 1.4;
      }

      .card-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;

        .due-date {
          font-size: 11px;
          color: #909399;
        }
      }

      .card-assignee {
        font-size: 11px;
      }
    }
  }
}

.task-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.task-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 18px;
  }
}

.detail-section {
  margin-top: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
  }
}

.detail-actions {
  margin: 16px 0;
}

.subtask-list {
  .subtask-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;

    .is-done {
      text-decoration: line-through;
      color: #909399;
    }
  }
}

.subtask-add, .comment-add {
  margin-top: 12px;
}

.comments-list {
  .comment-item {
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;

    .comment-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;

      .comment-time {
        font-size: 12px;
        color: #909399;
      }
    }

    .comment-content {
      font-size: 13px;
      margin: 0;
    }
  }
}
</style>
