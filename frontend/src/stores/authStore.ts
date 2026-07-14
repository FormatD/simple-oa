/** Auth store: manages JWT tokens, user info, and login state. */
import { defineStore } from "pinia"
import { ref, computed } from "vue"
import http from "@/api/client"
import type {
  APIResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserInfo,
} from "@/types/auth"

export const useAuthStore = defineStore(
  "auth",
  () => {
    const accessToken = ref<string | null>(null)
    const refreshTokenValue = ref<string | null>(null)
    const user = ref<UserInfo | null>(null)

    const isLoggedIn = computed(() => !!accessToken.value && !!user.value)
    const isSuperuser = computed(() => user.value?.is_superuser ?? false)

    async function login(credentials: LoginRequest) {
      const res = await http.post<APIResponse<TokenResponse>>(
        "/auth/login",
        credentials,
      )
      const data = res.data.data!
      accessToken.value = data.access_token
      refreshTokenValue.value = data.refresh_token
      await fetchUser()
    }

    async function register(data: RegisterRequest) {
      const res = await http.post<APIResponse<TokenResponse>>(
        "/auth/register",
        data,
      )
      const tokenData = res.data.data!
      accessToken.value = tokenData.access_token
      refreshTokenValue.value = tokenData.refresh_token
      await fetchUser()
    }

    async function fetchUser() {
      const res = await http.get<APIResponse<UserInfo>>("/auth/me")
      user.value = res.data.data!
    }

    async function refreshToken(): Promise<string> {
      const res = await http.post<APIResponse<TokenResponse>>("/auth/refresh", {
        refresh_token: refreshTokenValue.value,
      })
      const data = res.data.data!
      accessToken.value = data.access_token
      refreshTokenValue.value = data.refresh_token
      return data.access_token
    }

    function logout() {
      accessToken.value = null
      refreshTokenValue.value = null
      user.value = null
    }

    return {
      accessToken,
      refreshTokenValue,
      user,
      isLoggedIn,
      isSuperuser,
      login,
      register,
      fetchUser,
      refreshToken,
      logout,
    }
  },
  {
    persist: {
      key: "enterprise-auth",
      storage: localStorage,
      pick: ["accessToken", "refreshTokenValue", "user"],
    },
  },
)
