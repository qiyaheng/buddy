import { Button, Descriptions } from 'antd'
import { useAppStore } from '../../stores/app-store'

export default function AboutTab() {
  const { appVersion, platform, dataDir } = useAppStore()

  return (
    <div className="settings-pane">
      <p className="settings-section-desc">应用信息与本地数据位置。</p>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="应用名称">SMEbuddy AI 工作台</Descriptions.Item>
        <Descriptions.Item label="版本">v{appVersion}</Descriptions.Item>
        <Descriptions.Item label="运行平台">{platform || 'desktop'}</Descriptions.Item>
        <Descriptions.Item label="数据目录">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <code className="settings-mono">{dataDir || '-'}</code>
            {dataDir && (
              <Button size="small" onClick={() => void window.wb.openPath(dataDir)}>
                打开目录
              </Button>
            )}
          </div>
        </Descriptions.Item>
      </Descriptions>
      <div className="settings-notice">
        所有对话、配置与 API Key 均保存在本机数据目录中，Key 使用对称加密存储，不会上传到任何服务器。
      </div>
    </div>
  )
}
