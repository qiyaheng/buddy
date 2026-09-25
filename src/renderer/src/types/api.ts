/** 与后端 schemas 对应的接口契约（单一事实源在后端 Pydantic）。 */

export interface ModelConfig {
  id: string
  provider_id: string
  model_id: string
  display_name: string
  capabilities: string[]
  is_default: boolean
  sort_order: number
}

export interface Provider {
  id: string
  name: string
  base_url: string
  timeout_seconds: number
  enabled: boolean
  has_api_key: boolean
  api_key_masked: string
  models: ModelConfig[]
  created_at: string
}

export interface ProviderFormModel {
  model_id: string
  display_name: string
  capabilities: string[]
  is_default: boolean
}

export interface ProviderCreatePayload {
  name: string
  base_url: string
  api_key?: string | null
  timeout_seconds: number
  enabled: boolean
  models: ProviderFormModel[]
}

export interface ProviderUpdatePayload {
  name?: string
  base_url?: string
  api_key?: string | null
  timeout_seconds?: number
  enabled?: boolean
}

export interface SetupStatus {
  has_models: boolean
  default_provider_id: string | null
  default_model_id: string | null
  default_display_name: string | null
}

export interface AppSettings {
  search_provider: 'duckduckgo' | 'tavily'
  has_tavily_key: boolean
  tavily_api_key_masked: string
}

export interface ConnectionTestResult {
  ok: boolean
  code: string
  message: string
}

export type TaskStatus = 'idle' | 'running' | 'stopped' | 'error' | 'done'

export interface TaskSummary {
  id: string
  title: string
  status: TaskStatus
  folder_id: string | null
  expert_snapshot: ExpertSnapshot | null
  skill_snapshots: SkillSnapshot[]
  model_id: string | null
  model_snapshot: { id: string; model_id: string; display_name: string } | null
  error_message: string | null
  last_message_at: string | null
  created_at: string
  updated_at: string
}

export interface Folder {
  id: string
  name: string
  sort_order: number
  created_at: string
  updated_at: string
}

export interface ExpertSnapshot {
  id: string
  name: string
  emoji: string
  color: string
  system_prompt: string
}

export interface SkillSnapshot {
  id: string
  name: string
  icon: string
  prompt_template: string
  tools: string[]
}

export interface Expert {
  id: string
  name: string
  emoji: string
  color: string
  category: string
  tagline: string
  description: string
  system_prompt: string
  suggested_prompts: string[]
  is_builtin: boolean
  sort_order: number
}

export interface Skill {
  id: string
  name: string
  description: string
  prompt_template: string
  icon: string
  kind: 'builtin' | 'custom'
  is_builtin: boolean
  enabled: boolean
  sort_order: number
  tools: string[]
}

export interface ArtifactInfo {
  id: string
  task_id: string
  filename: string
  format: string
  kind: string
  size_bytes: number
  absolute_path: string
  created_at: string
}

export interface UsageSummary {
  request_count: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}
