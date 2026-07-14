/** Axios HTTP client with token refresh interceptor. */
import axios, { AxiosError, InternalAxiosRequestConfig } from "axios"
import { useAuthStore } from "@/stores/authStore"
import type { APIResponse } from "@/types/auth"

const http = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
})

// Request interceptor: attach access token
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: auto-refresh on 401
let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login") &&
      !originalRequest.url?.includes("/auth/register") &&
      !originalRequest.url?.includes("/auth/refresh")
    ) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(http(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const authStore = useAuthStore()
      try {
        const newToken = await authStore.refreshToken()
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        pendingRequests.forEach((cb) => cb(newToken))
        pendingRequests = []
        return http(originalRequest)
      } catch {
        authStore.logout()
        window.location.href = "/login"
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export default http
