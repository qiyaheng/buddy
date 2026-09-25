import { DoubleRightOutlined } from '@ant-design/icons'
import { Tabs, Tooltip } from 'antd'
import { useAppStore } from '../stores/app-store'

export default function ResultPanel() {
  const toggleRightCollapsed = useAppStore((s) => s.toggleRightCollapsed)

  return (
    <div className="wb-result-inner">
      <div className="wb-result-header">
        <Tabs
          defaultActiveKey="artifacts"
          size="small"
          style={{ flex: 1 }}
          items={[
            { key: 'artifacts', label: '产物' },
            { key: 'files', label: '全部文件' },
          ]}
        />
        <Tooltip title="收起面板">
          <button className="wb-icon-btn" onClick={toggleRightCollapsed} aria-label="收起产物面板">
            <DoubleRightOutlined />
          </button>
        </Tooltip>
      </div>
      <div className="wb-result-body">
        <div className="wb-result-empty">
          <div className="wb-result-empty-icon">📄</div>
          <div className="wb-result-empty-title">暂无产物</div>
          <div className="wb-result-empty-desc">
            任务生成的报告、文档、PPT
            <br />
            会自动出现在这里
          </div>
        </div>
      </div>
    </div>
  )
}
