/** Data import TypeScript types. */

export interface ImportRowPreview {
  row_number: number
  data: Record<string, string>
  valid: boolean
  errors: string[]
}

export interface ImportPreview {
  import_type: string
  filename: string
  total_rows: number
  valid_rows: number
  error_rows: number
  rows: ImportRowPreview[]
}

export interface ImportResult {
  id: string
  import_type: string
  filename: string
  total_rows: number
  success_rows: number
  error_rows: number
  status: string
  errors?: { row: number; error: string }[] | null
  summary?: Record<string, unknown> | null
  created_at: string
}

export interface ImportRecord {
  id: string
  import_type: string
  filename: string
  total_rows: number
  success_rows: number
  error_rows: number
  status: string
  summary?: Record<string, unknown> | null
  imported_by: string
  created_at: string
}

export interface DashboardStats {
  total_employees: number
  active_employees: number
  department_count: number
  pending_leave_count: number
  today_attendance_rate: number
  pending_tasks: number
  overdue_tasks: number
  training_count: number
}
