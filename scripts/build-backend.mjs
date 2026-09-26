/**
 * 使用 PyInstaller 将 FastAPI 后端打包为单文件二进制（Task 16 打包链路）。
 * Windows 产物：resources/backend/backend.exe
 * macOS 产物：resources/backend/backend（需在 macOS 上执行，PyInstaller 不支持交叉编译）
 */
import { existsSync, mkdirSync, rmSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const root = process.cwd()
const isWin = process.platform === 'win32'
const venvPython = isWin
  ? join(root, 'backend', '.venv', 'Scripts', 'python.exe')
  : join(root, 'backend', '.venv', 'bin', 'python')
const backendDir = join(root, 'backend')
const outDir = join(root, 'resources', 'backend')

if (!existsSync(venvPython)) {
  console.error('未找到 backend/.venv，请先运行 npm run predev')
  process.exit(1)
}

mkdirSync(outDir, { recursive: true })

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, { stdio: 'inherit', shell: isWin, ...options })
  if (result.status !== 0) process.exit(result.status ?? 1)
}

// Windows 下 shell:true 会原样拼接参数，>= 中的 > 会被 cmd 当成重定向符（产生杂散文件 6.0），需加引号
const pyinstallerSpec = isWin ? '"pyinstaller>=6.0"' : 'pyinstaller>=6.0'
run(venvPython, ['-m', 'pip', 'install', '--disable-pip-version-check', pyinstallerSpec])

// 清理旧产物
rmSync(join(backendDir, 'build'), { recursive: true, force: true })
rmSync(join(outDir, 'backend.exe'), { force: true })
rmSync(join(outDir, 'backend'), { force: true })

run(
  venvPython,
  [
    '-m',
    'PyInstaller',
    '--noconfirm',
    '--onefile',
    '--name',
    'backend',
    '--distpath',
    join('..', 'resources', 'backend'),
    '--workpath',
    'build',
    '--specpath',
    'build',
    '--collect-submodules',
    'trafilatura',
    '--collect-submodules',
    'duckduckgo_search',
    'entry.py',
  ],
  { cwd: backendDir },
)

console.log('[build-backend] 产物位于', outDir)
