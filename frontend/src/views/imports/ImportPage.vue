<template>
  <div class="import-page">
    <h2 class="page-title">数据导入</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="导入数据" name="import">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>选择导入类型</span>
          </template>
          <el-radio-group v-model="importType" class="import-type-group">
            <el-radio-button value="employee">员工数据</el-radio-button>
            <el-radio-button value="department">部门数据</el-radio-button>
            <el-radio-button value="position">岗位数据</el-radio-button>
          </el-radio-group>

          <el-divider />

          <el-upload
            drag
            :auto-upload="false"
            accept=".csv,.xlsx"
            :on-change="handleFileChange"
            class="upload-area"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              将 CSV 文件拖到此处，或<em>点击选择</em>
            </div>
            <template #tip>
              <div class="upload-tip">
                支持 .csv 格式，第一行为列标题
              </div>
            </template>
          </el-upload>

          <div v-if="previewData" class="preview-section">
            <el-divider />
            <h3>导入预览</h3>
            <el-alert
              :title="`共 ${previewData.total_rows} 行，有效 ${previewData.valid_rows} 行，错误 ${previewData.error_rows} 行`"
              :type="previewData.error_rows > 0 ? 'warning' : 'success'"
              show-icon
              :closable="false"
              class="preview-alert"
            />

            <el-table :data="previewData.rows" max-height="300" border class="preview-table">
              <el-table-column prop="row_number" label="行号" width="60" />
              <el-table-column label="数据" min-width="300">
                <template #default="{ row }">
                  <pre class="row-data">{{ JSON.stringify(row.data, null, 1) }}</pre>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.valid ? 'success' : 'danger'" size="small">
                    {{ row.valid ? '有效' : '错误' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="错误信息" min-width="200">
                <template #default="{ row }">
                  <span v-if="row.errors.length" class="error-text">{{
                    row.errors.join("; ")
                  }}</span>
                </template>
              </el-table-column>
            </el-table>

            <div class="preview-actions">
              <el-button @click="resetImport">取消</el-button>
              <el-button
                type="primary"
                :disabled="previewData.valid_rows === 0 || importing"
                :loading="importing"
                @click="confirmImport"
              >
                确认导入 ({{ previewData.valid_rows }} 条)
              </el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="导入记录" name="records">
        <el-card shadow="never">
          <el-table :data="importRecords" v-loading="loadingRecords">
            <el-table-column prop="import_type" label="类型" width="100">
              <template #default="{ row }">
                {{ { employee: "员工", department: "部门", position: "岗位" }[row.import_type] || row.import_type }}
              </template>
            </el-table-column>
            <el-table-column prop="filename" label="文件名" min-width="150" />
            <el-table-column prop="total_rows" label="总行数" width="80" />
            <el-table-column prop="success_rows" label="成功" width="80" />
            <el-table-column prop="error_rows" label="失败" width="80" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'completed' ? 'success' : row.status === 'completed_with_errors' ? 'warning' : 'info'"
                  size="small"
                >
                  {{ { completed: "完成", completed_with_errors: "部分失败", processing: "处理中", failed: "失败" }[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="170" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { ElMessage } from "element-plus"
import http from "@/api/client"
import type { APIResponse } from "@/types/auth"
import type { ImportPreview, ImportResult, ImportRecord } from "@/types/imports"

const activeTab = ref("import")
const importType = ref("employee")
const selectedFile = ref<File | null>(null)
const previewData = ref<ImportPreview | null>(null)
const importing = ref(false)
const importRecords = ref<ImportRecord[]>([])
const loadingRecords = ref(false)

function handleFileChange(file: any) {
  selectedFile.value = file.raw
  previewImport()
}

async function previewImport() {
  if (!selectedFile.value) return

  const formData = new FormData()
  formData.append("file", selectedFile.value)
  formData.append("import_type", importType.value)

  try {
    const res = await http.post<APIResponse<ImportPreview>>("/imports/preview", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    previewData.value = res.data.data!
  } catch {
    ElMessage.error("预览失败")
  }
}

async function confirmImport() {
  if (!previewData.value) return
  importing.value = true

  try {
    const validRows = previewData.value.rows
      .filter((r) => r.valid)
      .map((r) => r.data)

    const res = await http.post<APIResponse<ImportResult>>("/imports/confirm", {
      import_type: importType.value,
      filename: previewData.value.filename,
      rows: validRows,
    })
    const result = res.data.data!
    ElMessage.success(`导入完成: ${result.success_rows} 成功, ${result.error_rows} 失败`)
    resetImport()
    loadImportRecords()
  } catch {
    ElMessage.error("导入失败")
  } finally {
    importing.value = false
  }
}

function resetImport() {
  selectedFile.value = null
  previewData.value = null
}

async function loadImportRecords() {
  loadingRecords.value = true
  try {
    const res = await http.get<APIResponse<{ data: ImportRecord[] }>>("/imports/records?page_size=20")
    importRecords.value = res.data.data!.data
  } catch {
    // ignore
  } finally {
    loadingRecords.value = false
  }
}

onMounted(() => {
  loadImportRecords()
})
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 20px;
  font-size: 22px;
  color: #303133;
}
.import-type-group {
  margin-bottom: 16px;
}
.upload-area {
  margin-bottom: 16px;
}
.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 8px;
}
.upload-text {
  font-size: 14px;
  color: #606266;
}
.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
.preview-section {
  margin-top: 16px;
}
.preview-alert {
  margin-bottom: 16px;
}
.preview-table {
  margin-bottom: 16px;
  .row-data {
    margin: 0;
    font-size: 12px;
    white-space: pre-wrap;
  }
  .error-text {
    color: #f56c6c;
    font-size: 12px;
  }
}
.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
.section-card {
  margin-bottom: 20px;
}
</style>
