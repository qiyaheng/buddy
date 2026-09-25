import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import { join } from 'node:path'
import { loadingDataUrl } from './loading'
import { startSidecar, type SidecarHandle } from './sidecar'

let mainWindow: BrowserWindow | null = null
let sidecar: SidecarHandle | null = null

const isDev = !!process.env.ELECTRON_RENDERER_URL

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 684,
    show: false,
    backgroundColor: '#f5f6f8',
    title: 'SMEbuddy 工作台',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  win.once('ready-to-show', () => win.show())

  win.webContents.setWindowOpenHandler((details) => {
    if (details.url.startsWith('http://') || details.url.startsWith('https://')) {
      shell.openExternal(details.url)
    }
    return { action: 'deny' }
  })

  return win
}

async function bootstrap(): Promise<void> {
  mainWindow = createWindow()
  await mainWindow.loadURL(loadingDataUrl())

  try {
    sidecar = await startSidecar(isDev)
  } catch (err) {
    dialog.showErrorBox('本地引擎启动失败', err instanceof Error ? err.message : String(err))
    app.quit()
    return
  }

  if (!mainWindow || mainWindow.isDestroyed()) return

  if (isDev && process.env.ELECTRON_RENDERER_URL) {
    await mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    await mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function shutdown(): void {
  sidecar?.stop()
  sidecar = null
}

app.whenReady().then(() => {
  bootstrap().catch((err) => {
    console.error('[main] bootstrap failed', err)
    dialog.showErrorBox('启动失败', String(err))
    app.quit()
  })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  shutdown()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', shutdown)
process.on('exit', shutdown)

ipcMain.handle('app:get-context', () => ({
  apiBase: sidecar?.apiBase ?? '',
  version: app.getVersion(),
  platform: process.platform,
  isDev,
}))

ipcMain.handle('open-external', async (_event, url: string) => {
  if (typeof url === 'string' && /^https?:\/\//.test(url)) {
    await shell.openExternal(url)
  }
})

ipcMain.handle('shell:show-item', (_event, fullPath: string) => {
  shell.showItemInFolder(fullPath)
})

ipcMain.handle('shell:open-path', async (_event, fullPath: string) => {
  const error = await shell.openPath(fullPath)
  return { error: error || null }
})

ipcMain.handle('shell:save-as', async (_event, sourcePath: string, suggestedName?: string) => {
  if (!mainWindow) return { canceled: true }
  const result = await dialog.showSaveDialog(mainWindow, {
    defaultPath: suggestedName,
  })
  return { canceled: result.canceled, filePath: result.filePath ?? null, sourcePath }
})
