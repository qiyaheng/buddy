import { create } from 'zustand'
import { http } from '../lib/http'
import type { Expert } from '../types/api'

export interface ExpertFormValues {
  name: string
  emoji: string
  color: string
  category: string
  tagline: string
  description: string
  system_prompt: string
  suggested_prompts: string[]
}

type ExpertPayload = ExpertFormValues

interface ExpertsState {
  experts: Expert[]
  loading: boolean
  loaded: boolean

  refresh: () => Promise<void>
  create: (values: ExpertPayload) => Promise<Expert>
  update: (id: string, values: Partial<ExpertPayload>) => Promise<Expert>
  remove: (id: string) => Promise<void>
  duplicate: (id: string) => Promise<Expert>
}

export const useExpertsStore = create<ExpertsState>((set, get) => ({
  experts: [],
  loading: false,
  loaded: false,

  refresh: async () => {
    if (get().loading) return
    set({ loading: true })
    try {
      const experts = await http.get<Expert[]>('/api/experts')
      set({ experts, loaded: true })
    } finally {
      set({ loading: false })
    }
  },

  create: async (values) => {
    const expert = await http.post<Expert>('/api/experts', values)
    set((s) => ({ experts: [...s.experts, expert] }))
    return expert
  },

  update: async (id, values) => {
    const expert = await http.patch<Expert>(`/api/experts/${id}`, values)
    set((s) => ({
      experts: s.experts.map((e) => (e.id === id ? expert : e)),
    }))
    return expert
  },

  remove: async (id) => {
    await http.del(`/api/experts/${id}`)
    set((s) => ({ experts: s.experts.filter((e) => e.id !== id) }))
  },

  duplicate: async (id) => {
    const expert = await http.post<Expert>(`/api/experts/${id}/duplicate`, {})
    set((s) => ({ experts: [...s.experts, expert] }))
    return expert
  },
}))
