import { create } from 'zustand'
import { configureHttp, http, type AppContext } from '../lib/http'
import { configureSse } from '../lib/sse'
import type { SetupStatus } from '../types/api'

/**
 * 纯浏览器开发回退：没有 preload（window.wb）时，
 * 在 sidecar 常用端口范围内探测后端，仅用于本地 UI 联调。
 * 生产环境（Electron file://）始终走 window.wb.getContext()。
 */
async function discoverBrowserContext(): Promise<AppContext> {
  for (let port = 18790; port <= 18810; port += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/healthz`, { method: 'GET' })
      if (res.ok) {
        return { apiBase: `http://127.0.0.1:${port}`, version: '0.1.0', platform: 'browser', isDev: true }
      }
    } catch {
      // 端口未监听，继续探测
    }
  }
  throw new Error('未找到本地引擎（sidecar 未启动？）')
}

const PREFS_KEY = 'wb-prefs'

interface Prefs {
  leftWidth: number
  rightWidth: number
  rightCollapsed: boolean
}

const DEFAULT_PREFS: Prefs = {
  leftWidth: 248,
  rightWidth: 320,
  rightCollapsed: false,
}

function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) return { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<Prefs>) }
  } catch {
    // ignore
  }
  return DEFAULT_PREFS
}

interface AppState extends Prefs {
  ready: boolean
  bootError: string
  apiBase: string
  appVersion: string
  platform: string
  dataDir: string
  hasModels: boolean
  defaultModelId: string | null
  defaultModelName: string | null
  bootstrap: () => Promise<void>
  refreshSetup: () => Promise<SetupStatus>
  setLeftWidth: (width: number) => void
  setRightWidth: (width: number) => void
  toggleRightCollapsed: () => void
}

function persistPrefs(state: Pick<AppState, 'leftWidth' | 'rightWidth' | 'rightCollapsed'>): void {
  localStorage.setItem(
    PREFS_KEY,
    JSON.stringify({
      leftWidth: state.leftWidth,
      rightWidth: state.rightWidth,
      rightCollapsed: state.rightCollapsed,
    }),
  )
}

export const useAppStore = create<AppState>((set, get) => ({
  ...loadPrefs(),
  ready: false,
  bootError: '',
  apiBase: '',
  appVersion: '0.1.0',
  platform: '',
  dataDir: '',
  hasModels: false,
  defaultModelId: null,
  defaultModelName: null,

  bootstrap: async () => {
    try {
      const context =
        typeof window !== 'undefined' && window.wb
          ? await window.wb.getContext()
          : await discoverBrowserContext()
      configureHttp(context)
      configureSse(context.apiBase)
      const [health, status] = await Promise.all([
        http.get<{ data_dir: string; version: string }>('/healthz'),
        http.get<SetupStatus>('/api/setup/status'),
      ])
      set({
        ready: true,
        apiBase: context.apiBase,
        appVersion: context.version,
        platform: context.platform,
        dataDir: health.data_dir,
        hasModels: status.has_models,
        defaultModelId: status.default_model_id,
        defaultModelName: status.default_display_name,
      })
    } catch (err) {
      set({ ready: false, bootError: err instanceof Error ? err.message : String(err) })
    }
  },

  refreshSetup: async () => {
    const status = await http.get<SetupStatus>('/api/setup/status')
    set({
      hasModels: status.has_models,
      defaultModelId: status.default_model_id,
      defaultModelName: status.default_display_name,
    })
    return status
  },

  setLeftWidth: (width) => {
    set({ leftWidth: Math.min(340, Math.max(200, width)) })
    persistPrefs(get())
  },
  setRightWidth: (width) => {
    set({ rightWidth: Math.min(480, Math.max(260, width)) })
    persistPrefs(get())
  },
  toggleRightCollapsed: () => {
    set({ rightCollapsed: !get().rightCollapsed })
    persistPrefs(get())
  },
}))
