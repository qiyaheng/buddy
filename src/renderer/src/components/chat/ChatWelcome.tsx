import {
  BarChartOutlined,
  FileTextOutlined,
  SearchOutlined,
  SlidersOutlined,
} from '@ant-design/icons'

const SCENARIOS = [
  {
    icon: <SearchOutlined />,
    title: '深度调研',
    desc: '多源检索交叉验证，15 分钟交付研究报告',
    color: '#0891b2',
    prompt: '帮我深度调研 2025 年 AI 办公赛道的主要玩家、商业模式与趋势',
  },
  {
    icon: <FileTextOutlined />,
    title: '文档写作',
    desc: '周报、方案、PRD、公文，结构规范直接可用',
    color: '#4f7cff',
    prompt: '帮我写一份 Q3 季度工作总结，要求结构清晰、数据导向、突出重点项目',
  },
  {
    icon: <BarChartOutlined />,
    title: '数据分析',
    desc: '上传数据，自动分析洞察并给出行动建议',
    color: '#0ea5e9',
    prompt: '我会提供一份销售数据，请帮我分析趋势、异常点并给出行动建议',
  },
  {
    icon: <SlidersOutlined />,
    title: 'PPT 汇报',
    desc: '一句话生成演示文稿，结论先行有说服力',
    color: '#f97316',
    prompt: '帮我生成一份新产品发布汇报 PPT 大纲，结论先行，适合 10 分钟汇报',
  },
]

export default function ChatWelcome({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="chat-welcome">
      <div className="chat-hero-logo">S</div>
      <h1 className="chat-hero-title">一句话，把工作交给 AI 专家团</h1>
      <p className="chat-hero-sub">自主规划、调用工具、生成文件，从策略到交付一站搞定</p>
      <div className="chat-scenario-grid">
        {SCENARIOS.map((item) => (
          <button
            key={item.title}
            className="chat-scenario-card"
            onClick={() => onPick(item.prompt)}
          >
            <div className="chat-scenario-icon" style={{ color: item.color }}>
              {item.icon}
            </div>
            <div className="chat-scenario-name">{item.title}</div>
            <div className="chat-scenario-desc">{item.desc}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
