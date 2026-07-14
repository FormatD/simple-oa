/** Auth-related TypeScript types. */

export interface UserInfo {
  id: string
  email: string
  display_name: string
  phone?: string | null
  avatar_url?: string | null
  is_active: boolean
  is_superuser: boolean
  last_login_at?: string | null
  timezone: string
  locale: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name: string
  phone?: string
}

export interface APIResponse<T = any> {
  code: number
  message: string
  data?: T
}

export interface Organization {
  id: string
  name: string
  slug: string
  logo_url?: string | null
  description?: string | null
  owner_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Department {
  id: string
  organization_id: string
  parent_id?: string | null
  name: string
  path?: string | null
  sort_order: number
  children?: Department[] | null
  member_count?: number
}
