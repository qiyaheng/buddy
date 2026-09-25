import {
  ApiOutlined,
  FolderOutlined,
  GlobalOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { Spin, Tabs } from 'antd'
import { useEffect } from 'react'
import { useConfigStore } from '../../stores/config-store'
import AboutTab from './AboutTab'
import ConnectorsTab from './ConnectorsTab'
import ProvidersTab from './ProvidersTab'
import SearchTab from './SearchTab'

export default function SettingsPage() {
  const { loaded, loadAll } = useConfigStore()

  useEffect(() => {
    if (!loaded) void loadAll()
  }, [loaded, loadAll])

  if (!loaded) {
    return (
      <div className="page-simple">
        <Spin />
      </div>
    )
  }

  return (
    <div className="page-settings">
      <div className="settings-shell">
        <h2 className="settings-title">设置</h2>
        <Tabs
          tabPosition="left"
          className="settings-tabs"
          items={[
            { key: 'providers', label: <span><ApiOutlined /> 模型服务</span>, children: <ProvidersTab /> },
            { key: 'search', label: <span><GlobalOutlined /> 搜索与网络</span>, children: <SearchTab /> },
            { key: 'connectors', label: <span><FolderOutlined /> 连接器</span>, children: <ConnectorsTab /> },
            { key: 'about', label: <span><InfoCircleOutlined /> 关于</span>, children: <AboutTab /> },
          ]}
        />
      </div>
    </div>
  )
}
