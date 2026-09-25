/**
 * 开发前置：确保 backend/.venv 存在且依赖已安装。
 * 国内默认走清华镜像，可用 PIP_INDEX_URL 覆盖。
 */
import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const root = process.cwd()
const isWin = process.platform === 'win32'
const venvPython = isWin
  ? join(root, 'backend', '.venv', 'Scripts', 'python.exe')
  : join(root, 'backend', '.venv', 'bin', 'python')
const requirements = join(root, 'backend', 'requirements.txt')
const indexUrl = process.env.PIP_INDEX_URL ?? 'https://pypi.tuna.tsinghua.edu.cn/simple'

function run(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: 'inherit', shell: isWin })
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

if (!existsSync(venvPython)) {
  console.log('[ensure-venv] 创建 Python 虚拟环境 backend/.venv …')
  run(isWin ? 'python' : 'python3', ['-m', 'venv', join('backend', '.venv')])
}

console.log('[ensure-venv] 安装/校验后端依赖 …')
run(venvPython, [
  '-m',
  'pip',
  'install',
  '--disable-pip-version-check',
  '-i',
  indexUrl,
  '-r',
  requirements,
])

console.log('[ensure-venv] 后端环境就绪')
