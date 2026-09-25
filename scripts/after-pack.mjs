/**
 * electron-builder afterPack 钩子。
 * macOS：确保 PyInstaller 产出的 sidecar 二进制具备可执行权限，
 * 并在无 Developer ID 时做 ad-hoc 签名，降低 Gatekeeper 拦截概率。
 * Windows / Linux：无需处理。
 */
import { chmodSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'

export default function afterPack(context) {
  if (context.electronPlatformName !== 'mac') return

  const { appOutDir, packager } = context
  const appName = `${packager.appInfo.productFilename}.app`
  const appPath = join(appOutDir, appName)
  const sidecar = join(appPath, 'Contents', 'Resources', 'backend', 'backend')

  if (existsSync(sidecar)) {
    chmodSync(sidecar, 0o755)
    console.log('[afterPack] sidecar 已设置可执行权限:', sidecar)
  } else {
    console.warn('[afterPack] 未找到 sidecar:', sidecar)
  }

  // ad-hoc 签名（仅本机/内测分发；正式对外分发需改用 Developer ID + 公证）
  const result = spawnSync('codesign', ['--force', '--deep', '--sign', '-', appPath], {
    stdio: 'inherit',
  })
  if (result.status !== 0) {
    console.warn('[afterPack] ad-hoc codesign 失败，可稍后手动执行: codesign --force --deep --sign - <App.app>')
  }
}
