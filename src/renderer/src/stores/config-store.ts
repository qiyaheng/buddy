import { create } from 'zustand'
import { http } from '../lib/http'
import type {
  AppSettings,
  ConnectionTestResult,
  ModelConfig,
  Provider,
  ProviderCreatePayload,
  ProviderUpdatePayload,
} from '../types/api'

interface ConfigState {
  providers: Provider[]
  settings: AppSettings | null
  loaded: boolean
  loadAll: () => Promise<void>
  reloadProviders: () => Promise<void>
  reloadSettings: () => Promise<void>
  createProvider: (payload: ProviderCreatePayload) => Promise<Provider>
  updateProvider: (id: string, payload: ProviderUpdatePayload) => Promise<void>
  deleteProvider: (id: string) => Promise<void>
  addModel: (providerId: string, model: Omit<ModelConfig, 'id' | 'provider_id' | 'sort_order'>) => Promise<void>
  updateModel: (modelId: string, patch: Partial<ModelConfig>) => Promise<void>
  deleteModel: (modelId: string) => Promise<void>
  testConnection: (providerId: string, modelId?: string) => Promise<ConnectionTestResult>
  saveSettings: (payload: {
    search_provider?: 'duckduckgo' | 'tavily'
    tavily_api_key?: string
  }) => Promise<void>
  resetTavilyKey: () => Promise<void>
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  providers: [],
  settings: null,
  loaded: false,

  loadAll: async () => {
    const [providers, settings] = await Promise.all([
      http.get<Provider[]>('/api/providers'),
      http.get<AppSettings>('/api/settings'),
    ])
    set({ providers, settings, loaded: true })
  },

  reloadProviders: async () => {
    set({ providers: await http.get<Provider[]>('/api/providers') })
  },

  reloadSettings: async () => {
    set({ settings: await http.get<AppSettings>('/api/settings') })
  },

  createProvider: async (payload) => {
    const provider = await http.post<Provider>('/api/providers', payload)
    await get().reloadProviders()
    return provider
  },

  updateProvider: async (id, payload) => {
    await http.patch(`/api/providers/${id}`, payload)
    await get().reloadProviders()
  },

  deleteProvider: async (id) => {
    await http.del(`/api/providers/${id}`)
    await get().reloadProviders()
  },

  addModel: async (providerId, model) => {
    await http.post(`/api/providers/${providerId}/models`, model)
    await get().reloadProviders()
  },

  updateModel: async (modelId, patch) => {
    await http.patch(`/api/providers/models/${modelId}`, patch)
    await get().reloadProviders()
  },

  deleteModel: async (modelId) => {
    await http.del(`/api/providers/models/${modelId}`)
    await get().reloadProviders()
  },

  testConnection: async (providerId, modelId) => {
    return http.post<ConnectionTestResult>(`/api/providers/${providerId}/test`, {
      model_id: modelId ?? null,
    })
  },

  saveSettings: async (payload) => {
    await http.put('/api/settings', payload)
    await get().reloadSettings()
  },

  resetTavilyKey: async () => {
    await http.del('/api/settings/tavily_api_key')
    await get().reloadSettings()
  },
}))
