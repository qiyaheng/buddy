import { app } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createServer } from 'node:net'
import { join } from 'node:path'

export interface SidecarHandle {
  apiBase: string
  port: number
  stop: () => void
}

const isWindows = process.platform === 'win32'
const HOST = '127.0.0.1'
const PORT_START = 18790
const PORT_END = 18890

function repoRoot(): string {
  // 编译输出位于 out/main/index.js，仓库根在其上两级
  return join(__dirname, '..', '..')
}

function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const tryPort = (port: number) => {
      if (port > PORT_END) {
        reject(new Error('没有可用的本地端口'))
        return
      }
      const server = createServer()
      server.once('error', () => tryPort(port + 1))
      server.once('listening', () => {
        server.close(() => resolve(port))
      })
      server.listen(port, HOST)
    }
    tryPort(PORT_START)
  })
}

async function waitForHealth(apiBase: string, timeoutMs = 60_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  let lastError: unknown
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${apiBase}/healthz`, { signal: AbortSignal.timeout(1500) })
      if (res.ok) return
    } catch (err) {
      lastError = err
    }
    await new Promise((r) => setTimeout(r, 400))
  }
  throw new Error(`后端 sidecar 健康检查超时: ${String(lastError)}`)
}

function killProcessTree(child: ChildProcess): void {
  if (!child.pid) return
  if (isWindows) {
    spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true })
  } else {
    try {
      process.kill(-child.pid, 'SIGTERM')
    } catch {
      child.kill('SIGTERM')
    }
  }
}

export async function startSidecar(isDev: boolean): Promise<SidecarHandle> {
  const port = await findFreePort()
  const apiBase = `http://${HOST}:${port}`
  const dataDir = isDev ? join(repoRoot(), '.data') : join(app.getPath('userData'))

  let command: string
  let args: string[]
  let cwd: string

  if (isDev) {
    const venvPython = isWindows
      ? join(repoRoot(), 'backend', '.venv', 'Scripts', 'python.exe')
      : join(repoRoot(), 'backend', '.venv', 'bin', 'python')
    if (!existsSync(venvPython)) {
      throw new Error(`未找到后端虚拟环境: ${venvPython}，请先运行 npm run predev`)
    }
    command = venvPython
    args = ['-m', 'uvicorn', 'app.main:app', '--host', HOST, '--port', String(port)]
    cwd = join(repoRoot(), 'backend')
  } else {
    const exeName = isWindows ? 'backend.exe' : 'backend'
    command = join(process.resourcesPath, 'backend', exeName)
    if (!existsSync(command)) {
      throw new Error(`未找到打包后的后端程序: ${command}`)
    }
    args = ['--host', HOST, '--port', String(port)]
    cwd = join(process.resourcesPath, 'backend')
  }

  const child = spawn(command, args, {
    cwd,
    windowsHide: true,
    env: {
      ...process.env,
      SMEBUDDY_DATA_DIR: dataDir,
      SMEBUDDY_PORT: String(port),
      SMEBUDDY_PARENT_PID: String(process.pid),
    },
  })

  child.stdout?.on('data', (chunk) => {
    process.stdout.write(`[sidecar] ${chunk}`)
  })
  child.stderr?.on('data', (chunk) => {
    process.stderr.write(`[sidecar] ${chunk}`)
  })
  child.on('exit', (code, signal) => {
    console.log(`[sidecar] exited code=${code} signal=${signal}`)
  })

  const handle: SidecarHandle = {
    apiBase,
    port,
    stop: () => killProcessTree(child),
  }

  await waitForHealth(apiBase)
  return handle
}
