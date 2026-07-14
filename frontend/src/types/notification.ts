/** Notification module types */
export interface NotificationData {
  id: string
  organization_id: string
  type: string
  title: string
  content?: string | null
  sender_id?: string | null
  sender_name?: string | null
  source_type?: string | null
  source_id?: string | null
  metadata?: Record<string, any> | null
  is_read: boolean
  read_at?: string | null
  created_at: string
}

export interface UnreadCount {
  count: number
}

export interface NotificationPreference {
  id: string
  user_id: string
  notification_type: string
  channel_in_app: boolean
  channel_email: boolean
  digest: string
}
