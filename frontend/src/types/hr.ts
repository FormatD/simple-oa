/** HR module TypeScript types. */

export interface EmergencyContact {
  name: string
  relationship: string
  phone: string
}

export interface EmployeeBasic {
  id: string
  employee_no: string
  user_id: string
  display_name?: string | null
  email?: string | null
  department_id?: string | null
  department_name?: string | null
  position_id?: string | null
  position_name?: string | null
  reports_to?: string | null
  status: string
  employment_type: string
  hire_date: string
}

export interface EmployeeDetail extends EmployeeBasic {
  organization_id: string
  work_location?: string | null
  emergency_contact?: EmergencyContact | null
  created_at: string
  updated_at: string
}

export interface EmployeeCreateRequest {
  user_id: string
  employee_no: string
  department_id?: string | null
  position_id?: string | null
  reports_to?: string | null
  hire_date: string
  employment_type?: string
  work_location?: string | null
  emergency_contact?: EmergencyContact | null
}

export interface EmployeeUpdateRequest {
  department_id?: string | null
  position_id?: string | null
  reports_to?: string | null
  employment_type?: string | null
  work_location?: string | null
  emergency_contact?: EmergencyContact | null
}

export interface PositionData {
  id: string
  organization_id: string
  name: string
  description?: string | null
  sort_order: number
}

export interface AttendanceRecord {
  id: string
  employee_id: string
  date: string
  check_in_time?: string | null
  check_out_time?: string | null
  check_in_location?: { lat: number; lng: number } | null
  check_out_location?: { lat: number; lng: number } | null
  status: string
  overtime_hours?: number | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface AttendanceSummary {
  total_days: number
  present_days: number
  absent_days: number
  late_days: number
  early_leave_days: number
  leave_days: number
  overtime_hours: number
}

export interface LeaveTypeData {
  id: string
  organization_id: string
  name: string
  paid: boolean
  requires_approval: boolean
  max_days_per_year?: number | null
  min_notice_hours: number
  created_at: string
}

export interface LeaveBalance {
  id: string
  employee_id: string
  leave_type_id: string
  leave_type_name?: string | null
  total_days: number
  used_days: number
  pending_days: number
  remaining_days: number
  year: number
}

export interface LeaveRequestData {
  id: string
  employee_id: string
  employee_name?: string | null
  employee_no?: string | null
  leave_type_id: string
  leave_type_name?: string | null
  start_date: string
  end_date: string
  total_days: number
  reason?: string | null
  status: string
  approver_id?: string | null
  approver_name?: string | null
  proxy_approver_id?: string | null
  approved_at?: string | null
  rejection_reason?: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    page_size: number
    total: number
  }
}
