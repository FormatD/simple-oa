/** Training module TypeScript types. */

export interface TrainingInstructor {
  id: string
  organization_id: string
  name: string
  employee_id?: string | null
  title?: string | null
  expertise?: string | null
  bio?: string | null
  phone?: string | null
  email?: string | null
  is_external: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface TrainingCourse {
  id: string
  organization_id: string
  title: string
  description?: string | null
  category: string
  duration_hours?: number | null
  max_participants?: number | null
  credits?: number | null
  status: string
  cover_url?: string | null
  created_by: string
  created_at: string
  updated_at: string
}

export interface TrainingPlan {
  id: string
  course_id: string
  course_title?: string | null
  title: string
  start_date: string
  end_date: string
  start_time?: string | null
  end_time?: string | null
  location?: string | null
  instructor_id?: string | null
  instructor_name?: string | null
  max_participants?: number | null
  registered_count: number
  status: string
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface TrainingMaterial {
  id: string
  course_id: string
  name: string
  type: string
  file_url?: string | null
  description?: string | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface TrainingRegistration {
  id: string
  plan_id: string
  plan_title?: string | null
  employee_id: string
  employee_name?: string | null
  employee_no?: string | null
  status: string
  registered_at: string
  check_in_time?: string | null
  check_out_time?: string | null
  attendance_status?: string | null
  credits_earned?: number | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface TrainingEvaluation {
  id: string
  plan_id: string
  plan_title?: string | null
  employee_id: string
  employee_name?: string | null
  overall_rating?: number | null
  content_rating?: number | null
  instructor_rating?: number | null
  practical_rating?: number | null
  comment?: string | null
  submitted_at: string
}

export interface TrainingCertificate {
  id: string
  employee_id: string
  employee_name?: string | null
  employee_no?: string | null
  course_id: string
  course_title?: string | null
  plan_id?: string | null
  plan_title?: string | null
  certificate_no: string
  issued_date: string
  expiry_date?: string | null
  status: string
  file_url?: string | null
  created_at: string
  updated_at: string
}

export interface APIResponse<T = any> {
  code: number
  message: string
  data?: T
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    page_size: number
    total: number
  }
}
