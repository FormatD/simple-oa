<template>
  <div class="wiki-page">
    <div class="page-header">
      <h2>知识库</h2>
      <div class="header-actions">
        <el-button size="small" @click="fetchFolders">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- Sidebar: folder tree -->
      <el-col :span="5">
        <el-card shadow="never" class="sidebar-card">
          <template #header>
            <div class="sidebar-header">
              <span>文件夹</span>
              <el-button text size="small" @click="showCreateFolder = true">
                <el-icon><FolderAdd /></el-icon>
              </el-button>
            </div>
          </template>
          <div class="folder-tree">
            <div
              v-for="f in folders"
              :key="f.id"
              class="folder-item"
              :class="{ active: selectedFolder === f.id }"
              @click="selectFolder(f.id)"
            >
              <el-icon><Folder /></el-icon>
              <span>{{ f.name }}</span>
              <span class="page-count">{{ f.page_count }}</span>
            </div>
            <div v-if="!folders.length" class="empty-folder">
              <el-empty description="暂无文件夹" :image-size="60" />
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Main: page list & content -->
      <el-col :span="19">
        <el-card shadow="never">
          <template #header>
            <div class="main-header">
              <span>{{ selectedFolderName || '全部页面' }}</span>
              <el-button type="primary" size="small" @click="showCreatePage = true">
                <el-icon><Plus /></el-icon> 新建页面
              </el-button>
            </div>
          </template>

          <!-- Page List -->
          <div class="page-list">
            <div
              v-for="page in pages"
              :key="page.id"
              class="page-item"
              @click="openPage(page)"
            >
              <div class="page-item-title">
                <el-icon><Document /></el-icon>
                <span>{{ page.title }}</span>
              </div>
              <div class="page-item-meta">
                <span>{{ page.creator_name }}</span>
                <span>{{ formatDate(page.updated_at) }}</span>
              </div>
            </div>
            <el-empty v-if="!pages.length" description="暂无页面" :image-size="80" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Create Folder Dialog -->
    <el-dialog v-model="showCreateFolder" title="新建文件夹" width="400px">
      <el-form :model="folderForm">
        <el-form-item label="名称">
          <el-input v-model="folderForm.name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateFolder = false">取消</el-button>
        <el-button type="primary" @click="createFolder">创建</el-button>
      </template>
    </el-dialog>

    <!-- Create Page Dialog -->
    <el-dialog v-model="showCreatePage" title="新建页面" width="500px">
      <el-form :model="pageForm">
        <el-form-item label="标题">
          <el-input v-model="pageForm.title" />
        </el-form-item>
        <el-form-item label="文件夹">
          <el-select v-model="pageForm.folder_id" clearable style="width: 100%">
            <el-option
              v-for="f in folders"
              :key="f.id"
              :label="f.name"
              :value="f.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreatePage = false">取消</el-button>
        <el-button type="primary" @click="createPage">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue"
import { useRouter } from "vue-router"
import http from "@/api/client"
import type { WikiFolder, WikiPage } from "@/types/wiki"
import { ElMessage } from "element-plus"

const router = useRouter()

const folders = ref<WikiFolder[]>([])
const pages = ref<WikiPage[]>([])
const selectedFolder = ref<string | null>(null)
const showCreateFolder = ref(false)
const showCreatePage = ref(false)

const folderForm = reactive({ name: "" })
const pageForm = reactive({ title: "", folder_id: "" })

const selectedFolderName = computed(() => {
  if (!selectedFolder.value) return "全部页面"
  const findName = (items: WikiFolder[]): string => {
    for (const f of items) {
      if (f.id === selectedFolder.value) return f.name
      if (f.children) {
        const n = findName(f.children)
        if (n) return n
      }
    }
    return ""
  }
  return findName(folders.value)
})

async function fetchFolders() {
  try {
    const res = await http.get("/wiki/folders")
    if (res.data?.data) folders.value = res.data.data
  } catch (e) {
    console.error("Failed to fetch folders", e)
  }
}

async function fetchPages(folderId?: string | null) {
  try {
    // We use search to get all pages or filter by folder
    const params: Record<string, any> = {}
    if (folderId) params.folder_id = folderId
    // For now just fetch recent 50 pages
    const res = await http.get("/wiki/search", { params: { q: "" } })
    if (res.data?.data) {
      pages.value = folderId
        ? res.data.data.filter((p: WikiPage) => p.folder_id === folderId)
        : res.data.data
    }
  } catch (e) {
    console.error("Failed to fetch pages", e)
  }
}

function selectFolder(folderId: string | null) {
  selectedFolder.value = folderId
  fetchPages(folderId)
}

async function createFolder() {
  if (!folderForm.name) return
  try {
    await http.post("/wiki/folders", { name: folderForm.name })
    showCreateFolder.value = false
    folderForm.name = ""
    ElMessage.success("文件夹已创建")
    await fetchFolders()
  } catch {
    ElMessage.error("创建失败")
  }
}

async function createPage() {
  if (!pageForm.title) return
  try {
    const data: Record<string, any> = { title: pageForm.title, content: "" }
    if (pageForm.folder_id) data.folder_id = pageForm.folder_id
    const res = await http.post("/wiki/pages", data)
    showCreatePage.value = false
    pageForm.title = ""
    pageForm.folder_id = ""
    ElMessage.success("页面已创建")
    router.push(`/wiki/pages/${res.data.data.id}`)
  } catch {
    ElMessage.error("创建失败")
  }
}

function openPage(page: WikiPage) {
  router.push(`/wiki/pages/${page.id}`)
}

function formatDate(d: string) {
  return d ? d.slice(0, 10) : ""
}

onMounted(() => {
  fetchFolders()
  fetchPages()
})
</script>

<style scoped lang="scss">
.wiki-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h2 {
      margin: 0;
      font-size: 20px;
    }
  }

  .sidebar-card {
    :deep(.el-card__body) {
      padding: 8px;
    }
  }

  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .folder-tree {
    .folder-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px;
      cursor: pointer;
      border-radius: 4px;
      font-size: 13px;

      &:hover, &.active {
        background: #ecf5ff;
        color: #409eff;
      }

      .page-count {
        margin-left: auto;
        font-size: 11px;
        color: #909399;
      }
    }

    .empty-folder {
      padding: 20px 0;
    }
  }

  .main-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .page-list {
    .page-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid #f0f0f0;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #f5f7fa;
      }

      .page-item-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
      }

      .page-item-meta {
        display: flex;
        gap: 16px;
        font-size: 12px;
        color: #909399;
      }
    }
  }
}
</style>
