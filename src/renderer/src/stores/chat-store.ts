import { create } from 'zustand'
import { http } from '../lib/http'
import { streamPost } from '../lib/sse'
import { useTasksStore } from './tasks-store'
import type {
  PlanStep,
  RunEvent,
  UIBlock,
  UIMessage,
  UsageTally,
} from '../types/chat'
import type { TaskSummary, UsageSummary } from '../types/api'

export interface PendingExpert {
  id: string
  name: string
  emoji: string
  color: string
}

interface SendOptions {
  /** 显式指定专家（专家广场「开始任务」）；缺省沿用 pendingExpert。 */
  expertId?: string
}

interface ChatState {
  taskId: string | null
  task: TaskSummary | null
  messages: UIMessage[]
  running: boolean
  draft: string
  /** 预校验/网络级错误（消息级错误挂在 assistant 消息上）。 */
  notice: string | null
  usage: UsageTally | null
  /** 切换任务会话时丢弃上一个任务的迟到事件。 */
  sessionSeq: number
  /** 当前运行的中断控制器（不供 UI 直接使用）。 */
  abortController: AbortController | null
  /** 专家广场发起、尚未建任务时预选的专家（空白欢迎页展示）。 */
  pendingExpert: PendingExpert | null
  /** 随预选专家一并带入、到达空白页即自动发送的开场问题。 */
  pendingPrompt: string | null
  /** 当前会话选中的 ModelConfig 主键；null = 跟随任务绑定或全局默认。 */
  selectedModelId: string | null

  setDraft: (text: string) => void
  setSelectedModelId: (id: string | null) => void
  startBlank: () => void
  /** 专家广场入口：预选专家并可附带开场问题。 */
  setPendingStart: (expert: PendingExpert, prompt?: string | null) => void
  clearPending: () => void
  loadTask: (taskId: string) => Promise<void>
  send: (
    content: string,
    navigate?: (to: string, opts?: { replace?: boolean }) => void,
    options?: SendOptions,
  ) => Promise<void>
  stop: () => Promise<void>
  retryLast: () => Promise<void>
  renameTask: (title: string) => Promise<void>
  clearNotice: () => void
}

/** 与后端 runner.apply_event 同构的过程块归并。 */
function mergeEvent(
  blocks: UIBlock[],
  content: { value: string },
  ev: RunEvent,
  planIndex: Map<string, number>,
  thinkIndex: Map<string, number>,
  toolIndex: Map<string, number>,
): void {
  switch (ev.type) {
    case 'plan_start': {
      const steps: PlanStep[] = (ev.steps ?? []).map((s) => ({
        id: s.id,
        title: s.title,
        status: 'pending',
      }))
      const idx = blocks.length
      blocks.push({ type: 'plan', steps })
      for (const step of steps) planIndex.set(step.id, idx)
      return
    }
    case 'plan_update': {
      if (!ev.step_id) return
      const idx = planIndex.get(ev.step_id)
      const block = idx !== undefined ? (blocks[idx] as { steps: PlanStep[] }) : undefined
      const step = block?.steps.find((s) => s.id === ev.step_id)
      if (step && (ev.status === 'running' || ev.status === 'done' || ev.status === 'error')) {
        step.status = ev.status
      }
      return
    }
    case 'think_start': {
      if (!ev.id) return
      const idx = blocks.length
      blocks.push({ type: 'think', id: ev.id, text: '' })
      thinkIndex.set(ev.id, idx)
      return
    }
    case 'think_delta': {
      if (!ev.id) return
      const idx = thinkIndex.get(ev.id)
      if (idx !== undefined) {
        const block = blocks[idx] as { text: string }
        block.text += ev.delta ?? ''
      }
      return
    }
    case 'tool_call': {
      if (!ev.id || !ev.name) return
      const idx = blocks.length
      blocks.push({
        type: 'tool',
        id: ev.id,
        name: ev.name,
        status: 'started',
        input_summary: ev.input_summary ?? '',
      })
      toolIndex.set(ev.id, idx)
      return
    }
    case 'tool_result': {
      if (!ev.id) return
      const idx = toolIndex.get(ev.id)
      if (idx !== undefined) {
        const prev = blocks[idx]
        if (prev.type === 'tool') {
          blocks[idx] = {
            ...prev,
            status: ev.status === 'error' ? 'error' : 'finished',
            summary: ev.summary ?? '',
            sources: ev.sources ?? [],
            elapsed_ms: ev.elapsed_ms,
          }
        }
      }
      return
    }
    case 'message_delta': {
      content.value += ev.delta ?? ''
      return
    }
    case 'artifact': {
      blocks.push({
        type: 'artifact',
        id: ev.id ?? '',
        filename: ev.filename ?? '',
        format: ev.format ?? '',
        kind: ev.kind ?? '',
        size_bytes: ev.size_bytes ?? 0,
      })
      return
    }
    default:
      return
  }
}

function messageUpdater(
  messages: UIMessage[],
  messageId: string,
  fn: (m: UIMessage) => UIMessage,
): UIMessage[] {
  return messages.map((m) => (m.id === messageId ? fn(m) : m))
}

export const useChatStore = create<ChatState>((set, get) => ({
  taskId: null,
  task: null,
  messages: [],
  running: false,
  draft: '',
  notice: null,
  usage: null,
  sessionSeq: 0,
  abortController: null,
  pendingExpert: null,
  pendingPrompt: null,
  selectedModelId: null,

  setDraft: (text) => set({ draft: text }),
  setSelectedModelId: (id) => set({ selectedModelId: id }),
  clearNotice: () => set({ notice: null }),

  setPendingStart: (expert, prompt = null) =>
    set({ pendingExpert: expert, pendingPrompt: prompt }),

  clearPending: () => set({ pendingExpert: null, pendingPrompt: null }),

  startBlank: () =>
    set((s) => ({
      taskId: null,
      task: null,
      messages: [],
      running: false,
      notice: null,
      usage: null,
      selectedModelId: null,
      // pendingExpert/pendingPrompt 由专家广场注入，startBlank 不可清掉
      sessionSeq: s.sessionSeq + 1,
    })),

  loadTask: async (taskId) => {
    // send() 新建任务后 navigate 到同一路由：该任务的流式状态已由 send 接管，
    // 不能重置（否则 running 被清、sessionSeq 漂移会丢弃进行中的事件）。
    if (get().taskId === taskId && get().task?.id === taskId) return
    const seq = get().sessionSeq + 1
    set({
      sessionSeq: seq,
      taskId,
      running: false,
      notice: null,
      messages: [],
      usage: null,
      pendingExpert: null,
      pendingPrompt: null,
    })
    try {
      const [task, rawMessages, usageSummary] = await Promise.all([
        http.get<TaskSummary>(`/api/tasks/${taskId}`),
        http.get<UIMessage[]>(`/api/tasks/${taskId}/messages`),
        http.get<UsageSummary>(`/api/tasks/${taskId}/usage`),
      ])
      if (get().sessionSeq !== seq) return
      set({
        task,
        selectedModelId: task.model_id,
        messages: rawMessages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          blocks: (m.blocks ?? []) as UIBlock[],
          status: m.status,
          error_text: m.error_text ?? null,
          created_at: m.created_at,
        })),
        usage:
          usageSummary.total_tokens > 0
            ? {
                prompt_tokens: usageSummary.prompt_tokens,
                completion_tokens: usageSummary.completion_tokens,
                total_tokens: usageSummary.total_tokens,
              }
            : null,
      })
    } catch {
      if (get().sessionSeq === seq) set({ notice: '任务加载失败，请稍后重试' })
    }
  },

  send: async (content, navigate, options) => {
    const text = content.trim()
    if (!text || get().running) return

    let { taskId } = get()
    const expertId = options?.expertId ?? get().pendingExpert?.id
    const modelConfigId = get().selectedModelId
    set({ notice: null, draft: '', running: true })
    const seq = get().sessionSeq
    const controller = new AbortController()
    set({ abortController: controller })

    try {
      // 无当前任务：先建任务（标题取首句、携带专家快照）再跳转
      if (!taskId) {
        const title = text.replace(/\s+/g, ' ').slice(0, 20)
        const task = await http.post<TaskSummary>('/api/tasks', {
          title,
          ...(expertId ? { expert_id: expertId } : {}),
          ...(modelConfigId ? { model_config_id: modelConfigId } : {}),
        })
        if (get().sessionSeq !== seq) return
        taskId = task.id
        set({ taskId, task, pendingExpert: null, pendingPrompt: null })
        void useTasksStore.getState().refresh()
        navigate?.(`/chat/${taskId}`, { replace: true })
      }

      const planIndex = new Map<string, number>()
      const thinkIndex = new Map<string, number>()
      const toolIndex = new Map<string, number>()
      let assistantId = ''
      let userId = ''
      let assistantStatus: UIMessage['status'] = 'streaming'
      let assistantError: string | null = null
      let finalUsage: UsageTally | null = null

      await streamPost(`/api/tasks/${taskId}/runs`, {
        body: { content: text, ...(modelConfigId ? { model_config_id: modelConfigId } : {}) },
        signal: controller.signal,
        onEvent: (raw) => {
          if (get().sessionSeq !== seq) return
          const ev = raw as RunEvent
          if (ev.type === 'run_started') {
            userId = ev.user_message_id ?? ''
            assistantId = ev.assistant_message_id ?? ''
            // 任务此刻已在后端置为 running：刷新侧栏以亮起运行态指示点（并激活轮询）
            void useTasksStore.getState().refresh()
            set((s) => ({
              messages: [
                ...s.messages,
                {
                  id: userId,
                  role: 'user',
                  content: text,
                  blocks: [],
                  status: 'done',
                },
                {
                  id: assistantId,
                  role: 'assistant',
                  content: '',
                  blocks: [],
                  status: 'streaming',
                },
              ],
            }))
            return
          }

          if (ev.type === 'usage') {
            finalUsage = {
              prompt_tokens: ev.prompt_tokens ?? 0,
              completion_tokens: ev.completion_tokens ?? 0,
              total_tokens: ev.total_tokens ?? 0,
              latency_ms: ev.latency_ms ?? null,
            }
            return
          }

          if (ev.type === 'done') {
            assistantStatus = 'done'
            return
          }
          if (ev.type === 'stopped') {
            assistantStatus = 'stopped'
            return
          }
          if (ev.type === 'error') {
            assistantStatus = 'error'
            assistantError = ev.message ? `[${ev.code}] ${ev.message}` : '运行失败'
            return
          }

          set((s) => ({
            messages: messageUpdater(s.messages, assistantId, (m) => {
              const blocks = m.blocks.map((b) =>
                b.type === 'plan'
                  ? { type: 'plan' as const, steps: b.steps.map((step) => ({ ...step })) }
                  : b,
              )
              const draftContent = { value: m.content }
              mergeEvent(blocks, draftContent, ev, planIndex, thinkIndex, toolIndex)
              return { ...m, content: draftContent.value, blocks }
            }),
          }))
        },
      })

      if (get().sessionSeq !== seq) return
      // 流自然结束：写入最终状态/错误/用量
      set((s) => ({
        messages: messageUpdater(s.messages, assistantId, (m) => ({
          ...m,
          status: assistantStatus,
          error_text: assistantError,
        })),
        usage: finalUsage ?? s.usage,
        running: false,
        abortController: null,
      }))
      const task = await http.get<TaskSummary>(`/api/tasks/${taskId}`)
      if (get().sessionSeq === seq) set({ task })
      void useTasksStore.getState().refresh()
    } catch (err) {
      if (get().sessionSeq !== seq) return
      const aborted = controller.signal.aborted
      if (aborted) {
        // 主动停止：后端已收到 stop 或断链，本地即时收口
        set((s) => ({
          running: false,
          abortController: null,
          messages: s.messages.map((m) =>
            m.role === 'assistant' && m.status === 'streaming'
              ? { ...m, status: 'stopped' }
              : m,
          ),
        }))
      } else {
        const message =
          err instanceof Error && 'code' in err
            ? (err as Error).message
            : '网络异常，请检查后端服务是否运行'
        set((s) => ({
          running: false,
          abortController: null,
          notice: message,
          draft: text,
          messages: s.messages.map((m) =>
            m.role === 'assistant' && m.status === 'streaming'
              ? { ...m, status: 'error', error_text: message }
              : m,
          ),
        }))
      }
      if (taskId) {
        const refresh = async (): Promise<TaskSummary | null> =>
          http.get<TaskSummary>(`/api/tasks/${taskId}`).catch(() => null)
        let task = await refresh()
        // 后端 stopped 落库略晚于断链：拿到过时的 running 时短等重试一次
        if (task?.status === 'running') {
          await new Promise((r) => setTimeout(r, 800))
          const second = await refresh()
          if (second && second.status !== 'running') task = second
          else if (second) task = { ...second, status: 'stopped' as const }
        }
        if (task && get().sessionSeq === seq) set({ task })
        void useTasksStore.getState().refresh()
      }
    }
  },

  stop: async () => {
    const { taskId, abortController } = get()
    if (!taskId || !get().running) return
    await http.post(`/api/tasks/${taskId}/stop`, {}).catch(() => undefined)
    // 断流兜底（后端会在事件循环检查点收口为 stopped）
    abortController?.abort()
    // 乐观收口：stop 端点只发信号不等落库，避免标题栏短暂停留在「处理中」
    set((s) => ({
      running: false,
      abortController: null,
      task: s.task ? { ...s.task, status: 'stopped' } : s.task,
    }))
  },

  retryLast: async () => {
    const lastUser = [...get().messages].reverse().find((m) => m.role === 'user')
    if (lastUser) await get().send(lastUser.content)
  },

  renameTask: async (title) => {
    const { taskId } = get()
    const name = title.trim()
    if (!taskId || !name || get().task?.title === name) return
    const task = await http.patch<TaskSummary>(`/api/tasks/${taskId}`, { title: name })
    set({ task })
    void useTasksStore.getState().refresh()
  },
}))
