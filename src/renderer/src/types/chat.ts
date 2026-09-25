/** 对话区前端模型（与后端 Message.blocks JSON 结构对齐）。 */

export type PlanStepStatus = 'pending' | 'running' | 'done' | 'error'

export interface PlanStep {
  id: string
  title: string
  status: PlanStepStatus
}

export interface PlanBlock {
  type: 'plan'
  steps: PlanStep[]
}

export interface ThinkBlock {
  type: 'think'
  id: string
  text: string
}

export type ToolStatus = 'started' | 'finished' | 'error'

export interface ToolSource {
  title: string
  url: string
}

export interface ToolBlock {
  type: 'tool'
  id: string
  name: string
  status: ToolStatus
  input_summary: string
  summary?: string
  sources?: ToolSource[]
  elapsed_ms?: number
}

export interface ArtifactBlock {
  type: 'artifact'
  id: string
  filename: string
  format: string
  kind: string
  size_bytes: number
}

export type UIBlock = PlanBlock | ThinkBlock | ToolBlock | ArtifactBlock

export type UIMessageStatus = 'streaming' | 'done' | 'error' | 'stopped'

export interface UIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  blocks: UIBlock[]
  status: UIMessageStatus
  error_text?: string | null
  created_at?: string
}

/** 运行中最后一次 usage 事件累积值。 */
export interface UsageTally {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  latency_ms?: number | null
}

/** SSE run 事件（仅列出前端消费字段）。 */
export interface RunEvent {
  type:
    | 'run_started'
    | 'plan_start'
    | 'plan_update'
    | 'think_start'
    | 'think_delta'
    | 'tool_call'
    | 'tool_result'
    | 'message_delta'
    | 'artifact'
    | 'usage'
    | 'stopped'
    | 'error'
    | 'done'
  task_id?: string
  user_message_id?: string
  assistant_message_id?: string
  steps?: PlanStep[]
  step_id?: string
  status?: string
  id?: string
  delta?: string
  text?: never
  name?: string
  input_summary?: string
  summary?: string
  sources?: ToolSource[]
  elapsed_ms?: number
  filename?: string
  format?: string
  kind?: string
  size_bytes?: number
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  latency_ms?: number
  llm_requests?: number
  reason?: string
  code?: string
  message?: string
}
