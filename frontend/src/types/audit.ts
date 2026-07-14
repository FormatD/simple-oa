/** Audit log types */
export interface AuditLogEntry {
  id: string
  organization_id: string
  actor_id: string
  actor_name?: string | null
  actor_email?: string | null
  action: string
  resource_type: string
  resource_id?: string | null
  resource_name?: string | null
  details?: Record<string, any> | null
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
}
