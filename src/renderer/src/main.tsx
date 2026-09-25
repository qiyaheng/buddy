import { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { App as AntdApp, ConfigProvider, Spin } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppRouter from './App'
import { useAppStore } from './stores/app-store'
import './styles/global.css'

import type { ThemeConfig } from 'antd'

const theme: ThemeConfig = {
  token: {
    colorPrimary: '#4f7cff',
    colorInfo: '#4f7cff',
    colorLink: '#4f7cff',
    borderRadius: 10,
    fontSize: 14,
    colorText: '#1f2329',
    colorTextSecondary: '#646a73',
    colorBgLayout: '#f5f6f8',
    colorBorder: '#e8eaed',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
  components: {
    Button: { controlHeight: 36, fontWeight: 500 },
    Input: { controlHeight: 36 },
    Select: { controlHeight: 36 },
    Modal: { borderRadiusLG: 14 },
    Card: { borderRadiusLG: 14 },
    Tooltip: { borderRadius: 8 },
  },
}

function BootScreen({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="boot-page">
      <div className="boot-logo">S</div>
      <h1>SMEbuddy 工作台</h1>
      {error ? (
        <>
          <p className="boot-sub" style={{ color: '#ef4444', maxWidth: 420, textAlign: 'center' }}>
            本地引擎连接失败：{error}
          </p>
          <button className="boot-retry" onClick={onRetry}>
            重新连接
          </button>
        </>
      ) : (
        <>
          <p className="boot-sub">AI 智能体桌面工作台</p>
          <Spin />
          <p className="boot-data">正在启动本地引擎…</p>
        </>
      )}
    </div>
  )
}

function Root() {
  const { ready, bootError, bootstrap } = useAppStore()
  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  if (!ready) {
    return <BootScreen error={bootError} onRetry={() => void bootstrap()} />
  }

  return (
    <ConfigProvider theme={theme} locale={zhCN}>
      <AntdApp>
        <AppRouter />
      </AntdApp>
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(<Root />)
