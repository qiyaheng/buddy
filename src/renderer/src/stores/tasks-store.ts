import { create } from 'zustand'
import { http } from '../lib/http'
import type { Folder, TaskSummary } from '../types/api'

/** all=全部任务；ungrouped=未分组；folder:<id>=指定文件夹；search=关键词结果态 */
export type SidebarFilter = 'all' | 'ungrouped' | `folder:${string}` | 'search'

interface TasksState {
  tasks: TaskSummary[]
  folders: Folder[]
  loading: boolean
  filter: SidebarFilter
  query: string
  refresh: () => Promise<void>
  setFilter: (filter: SidebarFilter) => void
  setQuery: (query: string) => void
  renameTask: (taskId: string, title: string) => Promise<void>
  moveTask: (taskId: string, folderId: string | null) => Promise<void>
  removeTask: (taskId: string) => Promise<void>
  createFolder: (name: string) => Promise<void>
  renameFolder: (folderId: string, name: string) => Promise<void>
  removeFolder: (folderId: string) => Promise<void>
}

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: [],
  folders: [],
  loading: false,
  filter: 'all',
  query: '',

  refresh: async () => {
    set({ loading: true })
    try {
      const q = get().query.trim()
      const queryPath = q ? `/tasks?q=${encodeURIComponent(q)}` : '/tasks'
      const [tasks, folders] = await Promise.all([
        http.get<TaskSummary[]>(`/api${queryPath}`),
        http.get<Folder[]>('/api/folders'),
      ])
      set({ tasks, folders })
    } finally {
      set({ loading: false })
    }
  },

  setFilter: (filter) => set({ filter }),
  setQuery: (query) => {
    const trimmed = query
    set({ query: trimmed, filter: trimmed.trim() ? 'search' : 'all' })
  },

  renameTask: async (taskId, title) => {
    const name = title.trim()
    if (!name) return
    const task = await http.patch<TaskSummary>(`/api/tasks/${taskId}`, { title: name })
    set((s) => ({ tasks: s.tasks.map((t) => (t.id === taskId ? task : t)) }))
  },

  moveTask: async (taskId, folderId) => {
    // 显式传 null = 移动到未分组（exclude_unset 语义）
    const task = await http.patch<TaskSummary>(`/api/tasks/${taskId}`, { folder_id: folderId })
    set((s) => ({ tasks: s.tasks.map((t) => (t.id === taskId ? task : t)) }))
  },

  removeTask: async (taskId) => {
    await http.del<void>(`/api/tasks/${taskId}`)
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== taskId) }))
  },

  createFolder: async (name) => {
    const folderName = name.trim()
    if (!folderName) return
    const folder = await http.post<Folder>('/api/folders', { name: folderName })
    set((s) => ({ folders: [...s.folders, folder] }))
  },

  renameFolder: async (folderId, name) => {
    const folderName = name.trim()
    if (!folderName) return
    const folder = await http.patch<Folder>(`/api/folders/${folderId}`, { name: folderName })
    set((s) => ({ folders: s.folders.map((f) => (f.id === folderId ? folder : f)) }))
  },

  removeFolder: async (folderId) => {
    await http.del<void>(`/api/folders/${folderId}`)
    set((s) => ({
      folders: s.folders.filter((f) => f.id !== folderId),
      tasks: s.tasks.map((t) =>
        t.folder_id === folderId ? { ...t, folder_id: null } : t,
      ),
      filter: s.filter === `folder:${folderId}` ? 'ungrouped' : s.filter,
    }))
  },
}))
