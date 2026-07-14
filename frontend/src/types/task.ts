/** Task module types */
export interface TaskData {
  id: string
  organization_id: string
  project_id?: string | null
  assigner_id: string
  assigner_name?: string | null
  assignee_id?: string | null
  assignee_name?: string | null
  title: string
  description?: string | null
  status: string
  priority: string
  due_date?: string | null
  completed_at?: string | null
  tags?: string[] | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface KanbanColumn {
  status: string
  tasks: TaskData[]
}

export interface SubtaskData {
  id: string
  task_id: string
  title: string
  is_done: boolean
  sort_order: number
  assignee_id?: string | null
  assignee_name?: string | null
  created_at: string
  updated_at: string
}

export interface TaskComment {
  id: string
  task_id: string
  author_id: string
  author_name?: string | null
  author_avatar?: string | null
  parent_id?: string | null
  content: string
  mentions?: string[] | null
  created_at: string
  updated_at: string
}

export interface TaskActivity {
  id: string
  task_id: string
  actor_id: string
  actor_name?: string | null
  action: string
  field?: string | null
  old_value?: string | null
  new_value?: string | null
  metadata?: Record<string, any> | null
  created_at: string
}
