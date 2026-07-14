/** Wiki module types */
export interface WikiFolder {
  id: string
  organization_id: string
  parent_id?: string | null
  name: string
  sort_order: number
  created_by: string
  created_at: string
  updated_at: string
  children?: WikiFolder[] | null
  page_count?: number | null
}

export interface WikiPage {
  id: string
  organization_id: string
  folder_id?: string | null
  title: string
  content?: string | null
  content_html?: string | null
  format: string
  version: number
  is_published: boolean
  created_by: string
  creator_name?: string | null
  last_edited_by?: string | null
  editor_name?: string | null
  created_at: string
  updated_at: string
}

export interface WikiPageVersion {
  id: string
  page_id: string
  version: number
  title: string
  content?: string | null
  content_html?: string | null
  change_note?: string | null
  edited_by: string
  editor_name?: string | null
  created_at: string
}
