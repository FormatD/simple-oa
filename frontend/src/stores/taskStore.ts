/** Task Pinia store */
import { defineStore } from "pinia"
import http from "@/api/client"
import type { TaskData, KanbanColumn, SubtaskData, TaskComment, TaskActivity } from "@/types/task"

export const useTaskStore = defineStore("task", {
  state: () => ({
    tasks: [] as TaskData[],
    kanban: [] as KanbanColumn[],
    currentTask: null as TaskData | null,
    subtasks: [] as SubtaskData[],
    comments: [] as TaskComment[],
    activities: [] as TaskActivity[],
    loading: false,
    pagination: { page: 1, page_size: 20, total: 0 },
  }),

  actions: {
    async fetchTasks(params?: Record<string, any>) {
      this.loading = true
      try {
        const res = await http.get("/tasks", { params })
        if (res.data?.data) {
          this.tasks = res.data.data
          this.pagination = res.data.pagination || this.pagination
        }
      } catch (e) {
        console.error("Failed to fetch tasks", e)
      } finally {
        this.loading = false
      }
    },

    async fetchKanban() {
      this.loading = true
      try {
        const res = await http.get("/tasks/kanban")
        if (res.data?.data) {
          this.kanban = res.data.data
        }
      } catch (e) {
        console.error("Failed to fetch kanban", e)
      } finally {
        this.loading = false
      }
    },

    async fetchMyTasks(params?: Record<string, any>) {
      this.loading = true
      try {
        const res = await http.get("/tasks/my", { params })
        if (res.data?.data) {
          this.tasks = res.data.data
        }
      } finally {
        this.loading = false
      }
    },

    async createTask(data: Record<string, any>) {
      const res = await http.post("/tasks", data)
      if (res.data?.data) {
        this.tasks.unshift(res.data.data)
      }
      return res.data?.data
    },

    async updateTask(taskId: string, data: Record<string, any>) {
      const res = await http.put(`/tasks/${taskId}`, data)
      if (res.data?.data) {
        const idx = this.tasks.findIndex((t) => t.id === taskId)
        if (idx >= 0) this.tasks[idx] = res.data.data
        this.currentTask = res.data.data
      }
      return res.data?.data
    },

    async updateTaskStatus(taskId: string, status: string) {
      const res = await http.put(`/tasks/${taskId}/status`, { status })
      return res.data?.data
    },

    async reorderTask(taskId: string, status: string, sortOrder: number) {
      const res = await http.put(`/tasks/${taskId}/reorder`, { status, sort_order: sortOrder })
      return res.data?.data
    },

    async deleteTask(taskId: string) {
      await http.delete(`/tasks/${taskId}`)
      this.tasks = this.tasks.filter((t) => t.id !== taskId)
    },

    async fetchTaskDetail(taskId: string) {
      const res = await http.get(`/tasks/${taskId}`)
      if (res.data?.data) {
        this.currentTask = res.data.data
      }
      return res.data?.data
    },

    // Subtasks
    async fetchSubtasks(taskId: string) {
      const res = await http.get(`/tasks/${taskId}/subtasks`)
      if (res.data?.data) this.subtasks = res.data.data
    },

    async createSubtask(taskId: string, data: Record<string, any>) {
      const res = await http.post(`/tasks/${taskId}/subtasks`, data)
      if (res.data?.data) this.subtasks.push(res.data.data)
      return res.data?.data
    },

    async updateSubtask(taskId: string, subtaskId: string, data: Record<string, any>) {
      const res = await http.put(`/tasks/${taskId}/subtasks/${subtaskId}`, data)
      if (res.data?.data) {
        const idx = this.subtasks.findIndex((s) => s.id === subtaskId)
        if (idx >= 0) this.subtasks[idx] = res.data.data
      }
      return res.data?.data
    },

    async deleteSubtask(taskId: string, subtaskId: string) {
      await http.delete(`/tasks/${taskId}/subtasks/${subtaskId}`)
      this.subtasks = this.subtasks.filter((s) => s.id !== subtaskId)
    },

    // Comments
    async fetchComments(taskId: string) {
      const res = await http.get(`/tasks/${taskId}/comments`)
      if (res.data?.data) this.comments = res.data.data
    },

    async createComment(taskId: string, data: Record<string, any>) {
      const res = await http.post(`/tasks/${taskId}/comments`, data)
      if (res.data?.data) this.comments.push(res.data.data)
      return res.data?.data
    },

    async deleteComment(taskId: string, commentId: string) {
      await http.delete(`/tasks/${taskId}/comments/${commentId}`)
      this.comments = this.comments.filter((c) => c.id !== commentId)
    },

    // Activities
    async fetchActivities(taskId: string) {
      const res = await http.get(`/tasks/${taskId}/activities`)
      if (res.data?.data) this.activities = res.data.data
    },
  },
})
