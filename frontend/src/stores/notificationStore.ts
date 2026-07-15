/** Notification Pinia store with WebSocket support */
import { defineStore } from "pinia"
import http from "@/api/client"
import type { NotificationData, NotificationPreference } from "@/types/notification"

export const useNotificationStore = defineStore("notification", {
  state: () => ({
    notifications: [] as NotificationData[],
    unreadCount: 0,
    preferences: [] as NotificationPreference[],
    connected: false,
    ws: null as WebSocket | null,
  }),

  actions: {
    async fetchNotifications(params?: Record<string, any>) {
      try {
        const res = await http.get("/notifications", { params })
        if (res.data?.data) {
          this.notifications = res.data.data
        }
      } catch (e) {
        console.error("Failed to fetch notifications", e)
      }
    },

    async fetchUnreadCount() {
      try {
        const res = await http.get("/notifications/unread-count")
        if (res.data?.data) {
          this.unreadCount = res.data.data.count
        }
      } catch (e) {
        console.error("Failed to fetch unread count", e)
      }
    },

    async markRead(notifId: string) {
      await http.put(`/notifications/${notifId}/read`)
      const n = this.notifications.find((n) => n.id === notifId)
      if (n) {
        n.is_read = true
        this.unreadCount = Math.max(0, this.unreadCount - 1)
      }
    },

    async markAllRead() {
      await http.put("/notifications/read-all")
      this.notifications.forEach((n) => (n.is_read = true))
      this.unreadCount = 0
    },

    async fetchPreferences() {
      try {
        const res = await http.get("/notifications/preferences")
        if (res.data?.data) this.preferences = res.data.data
      } catch (e) {
        console.error("Failed to fetch preferences", e)
      }
    },

    async updatePreferences(prefs: NotificationPreference[]) {
      await http.put("/notifications/preferences", prefs)
    },

    connectWebSocket(accessToken: string) {
      if (this.ws) {
        this.ws.close()
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const wsUrl = `${protocol}//${window.location.host}/api/v1/notifications/ws`

      try {
        // Pass JWT via Sec-WebSocket-Protocol header instead of query param
        this.ws = new WebSocket(wsUrl, [accessToken])

        this.ws.onopen = () => {
          this.connected = true
        }

        this.ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            if (msg.event === "notification.new") {
              this.fetchUnreadCount()
              this.fetchNotifications({ page: 1, page_size: 10 })
            }
          } catch (e) {
            // ignore parse errors (e.g. pong)
          }
        }

        this.ws.onclose = () => {
          this.connected = false
          // Auto-reconnect after 5s
          setTimeout(() => {
            if (accessToken) this.connectWebSocket(accessToken)
          }, 5000)
        }

        this.ws.onerror = () => {
          this.ws?.close()
        }
      } catch (e) {
        console.error("WebSocket connection failed", e)
      }
    },

    disconnectWebSocket() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this.connected = false
    },
  },
})
