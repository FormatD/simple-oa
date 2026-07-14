<template>
  <div class="file-upload">
    <el-upload
      :action="uploadUrl"
      :headers="headers"
      :data="extraData"
      :on-success="handleSuccess"
      :on-error="handleError"
      :before-upload="beforeUpload"
      :file-list="fileList"
      :multiple="multiple"
      :limit="limit"
      :accept="accept"
      drag
    >
      <el-icon class="upload-icon" :size="40"><UploadFilled /></el-icon>
      <div class="upload-text">
        <span>拖拽文件到此处，或 <em>点击上传</em></span>
      </div>
      <template #tip>
        <div class="upload-tip">
          支持 jpg/png/pdf/docx 格式，单个文件不超过 50MB
        </div>
      </template>
    </el-upload>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { useAuthStore } from "@/stores/authStore"
import { ElMessage } from "element-plus"
import type { UploadProps, UploadUserFile } from "element-plus"

const props = withDefaults(defineProps<{
  sourceType?: string
  sourceId?: string
  multiple?: boolean
  limit?: number
  accept?: string
  fileList?: UploadUserFile[]
}>(), {
  multiple: false,
  limit: 1,
  accept: ".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx",
})

const emit = defineEmits<{
  success: [file: any]
  error: [error: any]
}>()

const authStore = useAuthStore()

const uploadUrl = "/api/v1/uploads"
const headers = computed(() => ({
  Authorization: `Bearer ${authStore.accessToken}`,
}))
const extraData = computed(() => {
  const data: Record<string, string> = {}
  if (props.sourceType) data.source_type = props.sourceType
  if (props.sourceId) data.source_id = props.sourceId
  return data
})

const handleSuccess: UploadProps["onSuccess"] = (response) => {
  if (response?.data) {
    ElMessage.success("文件上传成功")
    emit("success", response.data)
  }
}

const handleError: UploadProps["onError"] = () => {
  ElMessage.error("文件上传失败")
  emit("error", new Error("Upload failed"))
}

const beforeUpload: UploadProps["beforeUpload"] = (file) => {
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error("文件大小不能超过 50MB!")
    return false
  }
  return true
}
</script>

<style scoped lang="scss">
.file-upload {
  .upload-icon {
    margin-bottom: 8px;
  }
  .upload-text {
    font-size: 14px;
    em {
      color: #409eff;
      font-style: normal;
    }
  }
  .upload-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }
}
</style>
