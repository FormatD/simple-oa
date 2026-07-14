<template>
  <div class="wiki-editor-page">
    <!-- Loading -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else-if="page">
      <!-- Page Header -->
      <div class="editor-header">
        <div class="header-left">
          <el-button text @click="goBack">
            <el-icon><ArrowLeft /></el-icon> 返回
          </el-button>
          <el-tag v-if="page.version" size="small" type="info">
            v{{ page.version }}
          </el-tag>
        </div>
        <div class="header-actions">
          <el-button
            :type="editing ? 'primary' : 'default'"
            size="small"
            @click="toggleEdit"
          >
            <el-icon><Edit /></el-icon> {{ editing ? '预览' : '编辑' }}
          </el-button>
          <el-button
            v-if="editing"
            type="success"
            size="small"
            @click="savePage"
            :loading="saving"
          >
            保存
          </el-button>
          <el-dropdown trigger="click" v-if="versions.length">
            <el-button size="small">
              历史版本 <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="v in versions"
                  :key="v.id"
                  @click="restoreVersion(v)"
                >
                  v{{ v.version }} - {{ v.change_note || formatDate(v.created_at) }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- Editor / Viewer -->
      <el-card shadow="never" class="editor-card">
        <div v-if="editing" class="edit-mode">
          <el-input
            v-model="editTitle"
            placeholder="页面标题"
            class="title-input"
            size="large"
          />
          <el-input
            v-model="editContent"
            type="textarea"
            :rows="20"
            placeholder="支持 Markdown 格式..."
            class="content-textarea"
          />
          <div class="change-note">
            <el-input v-model="changeNote" placeholder="变更说明（选填）" size="small" />
          </div>
        </div>
        <div v-else class="view-mode">
          <h1 class="page-title">{{ page.title }}</h1>
          <div class="page-meta">
            <span>创建者: {{ page.creator_name }}</span>
            <span>最后编辑: {{ page.editor_name || page.creator_name }}</span>
            <span>{{ formatDate(page.updated_at) }}</span>
          </div>
          <el-divider />
          <div class="page-content">
            <pre>{{ page.content || '暂无内容' }}</pre>
          </div>
        </div>
      </el-card>
    </template>

    <el-empty v-else description="页面未找到" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import http from "@/api/client"
import type { WikiPage, WikiPageVersion } from "@/types/wiki"
import { ElMessage } from "element-plus"

const route = useRoute()
const router = useRouter()

const page = ref<WikiPage | null>(null)
const versions = ref<WikiPageVersion[]>([])
const loading = ref(true)
const editing = ref(false)
const saving = ref(false)

const editTitle = ref("")
const editContent = ref("")
const changeNote = ref("")

async function fetchPage() {
  const pageId = route.params.pageId as string
  if (!pageId) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const res = await http.get(`/wiki/pages/${pageId}`)
    if (res.data?.data) {
      page.value = res.data.data
      editTitle.value = res.data.data.title
      editContent.value = res.data.data.content || ""
    }
  } catch {
    page.value = null
  } finally {
    loading.value = false
  }
}

async function fetchVersions() {
  const pageId = route.params.pageId as string
  if (!pageId) return
  try {
    const res = await http.get(`/wiki/pages/${pageId}/versions`)
    if (res.data?.data) versions.value = res.data.data
  } catch {
    // ignore
  }
}

function toggleEdit() {
  if (editing) {
    editing.value = false
  } else {
    editing.value = true
  }
}

async function savePage() {
  if (!page.value) return
  saving.value = true
  try {
    const data: Record<string, any> = {
      title: editTitle.value,
      content: editContent.value,
    }
    if (changeNote.value) data.change_note = changeNote.value

    const res = await http.put(`/wiki/pages/${page.value.id}`, data)
    if (res.data?.data) {
      page.value = res.data.data
      editing.value = false
      changeNote.value = ""
      ElMessage.success("页面已保存")
      await fetchVersions()
    }
  } catch {
    ElMessage.error("保存失败")
  } finally {
    saving.value = false
  }
}

async function restoreVersion(v: WikiPageVersion) {
  if (!page.value) return
  try {
    await http.post(`/wiki/pages/${page.value.id}/versions/${v.version}/restore`)
    ElMessage.success("已恢复到 v" + v.version)
    await fetchPage()
    await fetchVersions()
  } catch {
    ElMessage.error("恢复失败")
  }
}

function goBack() {
  router.push("/wiki")
}

function formatDate(d: string) {
  return d ? d.slice(0, 10) : ""
}

onMounted(() => {
  fetchPage()
  fetchVersions()
})
</script>

<style scoped lang="scss">
.wiki-editor-page {
  .loading-wrap {
    padding: 40px;
  }

  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .editor-card {
    :deep(.el-card__body) {
      padding: 24px;
    }
  }

  .view-mode {
    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 12px;
    }

    .page-meta {
      display: flex;
      gap: 20px;
      font-size: 13px;
      color: #909399;
    }

    .page-content {
      font-size: 14px;
      line-height: 1.8;

      pre {
        white-space: pre-wrap;
        font-family: inherit;
        margin: 0;
      }
    }
  }

  .edit-mode {
    .title-input {
      margin-bottom: 16px;
      font-size: 18px;
      font-weight: 600;
    }

    .content-textarea {
      :deep(textarea) {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
      }
    }

    .change-note {
      margin-top: 12px;
    }
  }
}
</style>
