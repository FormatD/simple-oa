/** Training module TypeScript types. */

export interface TrainingCourse {
  id: string
  organization_id: string
  title: string
  description?: string | null
  instructor?: string | null
  start_date?: string | null
  end_date?: string | null
  duration_hours?: number | null
  max_participants?: number | null
  location?: string | null
  status: string
  category?: string | null
  enrollment_count: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface TrainingCourseCreateRequest {
  title: string
  description?: string | null
  instructor?: string | null
  start_date?: string | null
  end_date?: string | null
  duration_hours?: number | null
  max_participants?: number | null
  location?: string | null
  category?: string | null
}

export interface TrainingEnrollment {
  id: string
  course_id: string
  employee_id: string
  employee_name?: string | null
  employee_no?: string | null
  status: string
  attended?: boolean | null
  score?: number | null
  feedback?: string | null
  completed_at?: string | null
  created_at: string
}
