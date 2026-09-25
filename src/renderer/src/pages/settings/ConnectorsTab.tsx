import { Tag } from 'antd'

const CONNECTORS = [
  { name: 'Jira', emoji: '🧩', desc: '同步需求与缺陷，自动更新任务状态' },
  { name: 'Notion', emoji: '📔', desc: '读写页面与数据库，沉淀调研结论' },
  { name: 'Slack', emoji: '💬', desc: '发送汇报、接收定时任务通知' },
  { name: 'Google Drive', emoji: '📁', desc: '上传产物并共享给团队成员' },
  { name: 'GitHub', emoji: '🐙', desc: '读取仓库、创建 Issue 与 PR' },
  { name: '飞书', emoji: '🐦', desc: '文档与消息协作（规划中）' },
]

export default function ConnectorsTab() {
  return (
    <div className="settings-pane">
      <p className="settings-section-desc">接入企业生态，让专家团直接读写你的工作数据。</p>
      <div className="connector-grid">
        {CONNECTORS.map((item) => (
          <div className="connector-card" key={item.name}>
            <div className="connector-head">
              <span className="connector-emoji">{item.emoji}</span>
              <Tag color="default">即将推出</Tag>
            </div>
            <div className="connector-name">{item.name}</div>
            <div className="connector-desc">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
