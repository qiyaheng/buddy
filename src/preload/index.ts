import { contextBridge, ipcRenderer } from 'electron'

export interface AppContext {
  apiBase: string
  version: string
  platform: string
  isDev: boolean
}

const api = {
  getContext: (): Promise<AppContext> => ipcRenderer.invoke('app:get-context'),
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke('open-external', url),
  showItemInFolder: (fullPath: string): Promise<void> =>
    ipcRenderer.invoke('shell:show-item', fullPath),
  openPath: (fullPath: string): Promise<{ error: string | null }> =>
    ipcRenderer.invoke('shell:open-path', fullPath),
  showSaveDialog: (
    sourcePath: string,
    suggestedName?: string,
  ): Promise<{ canceled: boolean; filePath: string | null; sourcePath: string }> =>
    ipcRenderer.invoke('shell:save-as', sourcePath, suggestedName),
}

export type WbApi = typeof api

contextBridge.exposeInMainWorld('wb', api)
