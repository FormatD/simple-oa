<template>
  <el-popover
    placement="bottom-end"
    :width="360"
    trigger="click"
    @show="handleShow"
  >
    <template #reference>
      <el-badge :value="notificationStore.unreadCount" :hidden="notificationStore.unreadCount === 0" class="notification-badge">
        <el-icon :size="20" style="cursor: pointer"><Bell /></el-icon>
      </el-badge>
    </template>

    <div class="notification-popover">
      <div class="notif-header">
        <span class="notif-title">通知</span>
        <el-button
          v-if="notificationStore.unreadCount > 0"
          text
          size="small"
          @click="markAllRead"
        >
          全部已读
        </el-button>
      </div>

      <div class="notif-list">
        <div
          v-for="n in notificationStore.notifications.slice(0, 20)"
          :key="n.id"
          class="notif-item"
          :class="{ unread: !n.is_read }"
          @click="handleClick(n)"
        >
          <div class="notif-dot" v-if="!n.is_read" />
          <div class="notif-body">
            <div class="notif-title-text">{{ n.title }}</div>
            <div v-if="n.content" class="notif-content">{{ n.content }}</div>
            <div class="notif-time">{{ formatTime(n.created_at) }}</div>
          </div>
        </div>
        <el-empty v-if="!notificationStore.notifications.length" description="暂无通知" :image-size="40" />
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { onMounted } from "vue"
import { useNotificationStore } from "@/stores/notificationStore"
import type { NotificationData } from "@/types/notification"

const notificationStore = useNotificationStore()

function handleShow() {
  if (!notificationStore.notifications.length) {
    notificationStore.fetchNotifications({ page: 1, page_size: 20 })
  }
}

function handleClick(n: NotificationData) {
  if (!n.is_read) {
    notificationStore.markRead(n.id)
  }
}

function markAllRead() {
  notificationStore.markAllRead()
}

function formatTime(d: string) {
  if (!d) return ""
  const date = new Date(d)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return "刚刚"
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.slice(5, 10) + " " + d.slice(11, 16)
}

onMounted(() => {
  notificationStore.fetchUnreadCount()
})
</script>

<style scoped lang="scss">
.notification-popover {
  max-height: 480px;
  overflow-y: auto;

  .notif-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid #f0f0f0;
    margin-bottom: 8px;

    .notif-title {
      font-weight: 600;
      font-size: 14px;
    }
  }

  .notif-list {
    .notif-item {
      display: flex;
      gap: 8px;
      padding: 10px 0;
      cursor: pointer;
      border-bottom: 1px solid #f5f5f5;

      &:hover {
        background: #fafafa;
      }

      &.unread {
        background: #f0f9ff;
      }

      .notif-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #409eff;
        margin-top: 6px;
        flex-shrink: 0;
      }

      .notif-body {
        flex: 1;

        .notif-title-text {
          font-size: 13px;
          font-weight: 500;
        }

        .notif-content {
          font-size: 12px;
          color: #909399;
          margin-top: 2px;
        }

        .notif-time {
          font-size: 11px;
          color: #c0c4cc;
          margin-top: 4px;
        }
      }
    }
  }
}
</style>
