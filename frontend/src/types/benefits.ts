/** Benefits module TypeScript types. */

export interface BenefitItem {
  id: string
  organization_id: string
  name: string
  description?: string | null
  category?: string | null
  is_active: boolean
  annual_budget?: number | null
  created_at: string
  updated_at: string
}

export interface BenefitItemCreateRequest {
  name: string
  description?: string | null
  category?: string | null
  annual_budget?: number | null
}

export interface EmployeeBenefit {
  id: string
  employee_id: string
  employee_name?: string | null
  benefit_item_id: string
  benefit_item_name?: string | null
  effective_date: string
  expiry_date?: string | null
  amount?: number | null
  is_active: boolean
  created_at: string
}

export interface BenefitClaim {
  id: string
  employee_id: string
  employee_name?: string | null
  benefit_item_id: string
  benefit_item_name?: string | null
  claim_date: string
  amount: number
  description?: string | null
  status: string
  approved_by?: string | null
  approved_at?: string | null
  receipt_url?: string | null
  created_at: string
}

export interface BenefitClaimCreateRequest {
  benefit_item_id: string
  claim_date: string
  amount: number
  description?: string | null
  receipt_url?: string | null
}
