export type RunStatus =
  | 'CREATED'
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'PARTIAL'
  | 'FAILED'
  | 'CANCELLED';

export interface Run {
  id: string;
  city_input: string;
  city_normalized: string;
  category?: string;
  category_mode: string;
  confidence_threshold: number;
  requested_limit: number;
  status: RunStatus;
  started_at?: string;
  completed_at?: string;
  cancelled_at?: string;
  records_discovered: number;
  records_saved: number;
  records_failed: number;
  error_count: number;
  error_message?: string;
  created_at: string;
}

export interface FieldProvenance {
  id: string;
  field_name: string;
  field_value?: string;
  source_type: string;
  source_url?: string;
  extraction_method?: string;
  confidence?: number;
  extracted_at: string;
}

export interface Business {
  id: string;
  run_id: string;
  source: string;
  name: string;
  normalized_name: string;
  category?: string;
  subcategory?: string;
  address?: string;
  street?: string;
  locality?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  phone?: string;
  normalized_phone?: string;
  email?: string;
  website?: string;
  website_domain?: string;
  website_status?: string;
  rating?: number;
  review_count?: number;
  google_place_id?: string;
  google_profile_url?: string;
  opening_hours?: string;
  status: string;
  created_at: string;
  updated_at: string;
  provenances?: FieldProvenance[];
}

export interface PaginatedBusinesses {
  items: Business[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface CreateRunPayload {
  city: string;
  category: string;
  limit: number;
  confidence_threshold: number;
  start_immediately?: boolean;
}
