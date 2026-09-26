/**
 * electron-builder afterPack 钩子。
 * Windows：用原版 electron.exe 覆盖打包后的主程序。打包过程会对主程序注入 asar 完整性资源、
 * rcedit 版本信息，产生无微软云信誉的新哈希，被 Smart App Control 拦截；
 * 覆盖为全球通用的原版 electron（已验证 SAC 放行）。代价是无 asar 完整性校验和自定义 exe 图标。
 * macOS：确保 PyInstaller sidecar 可执行，并在无 Developer ID 时做 ad-hoc 签名。
 */
import { chmodSync, copyFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import { spawnSync } from 'node:child_process'

export default function afterPack(context) {
  const { appOutDir, packager } = context

  if (context.electronPlatformName === 'win32') {
    const exeName = `${packager.appInfo.productFilename}.exe`
    const target = join(appOutDir, exeName)
    const originalElectron = join(packager.projectDir, 'node_modules', 'electron', 'dist', 'electron.exe')
    if (!existsSync(originalElectron)) {
      throw new Error(`[afterPack] 未找到原版 electron: ${originalElectron}`)
    }
    copyFileSync(originalElectron, target)
    console.log('[afterPack] 已用原版 electron 覆盖主程序（SAC 兼容）:', target)
    return
  }

  if (context.electronPlatformName !== 'mac') return

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
