import { ExclamationCircleFilled, ReloadOutlined } from '@ant-design/icons'
import { Alert, Button } from 'antd'
import type { UIMessage } from '../../types/chat'
import type { ExpertSnapshot } from '../../types/api'
import Markdown from './Markdown'
import ArtifactBlock from './blocks/ArtifactBlock'
import PlanBlock from './blocks/PlanBlock'
import ThinkBlock from './blocks/ThinkBlock'
import ToolBlock from './blocks/ToolBlock'

interface Props {
  message: UIMessage
  expert: ExpertSnapshot | null
  onRetry: () => void
}

export default function AgentMessage({ message, expert, onRetry }: Props) {
  const streaming = message.status === 'streaming'
  const thinkIds = new Set(
    message.blocks.filter((b) => b.type === 'think').map((b) => b.id),
  )
  const lastThinkId = [...thinkIds].pop()

  return (
    <div className="msg msg-agent">
      <div
        className="msg-avatar"
        style={expert?.color ? { background: expert.color } : undefined}
      >
        {expert?.emoji ?? 'S'}
      </div>
      <div className="msg-body">
        <div className="msg-blocks">
          {message.blocks.map((block, i) => {
            if (block.type === 'plan') return <PlanBlock key={`plan-${i}`} block={block} />
            if (block.type === 'tool') return <ToolBlock key={block.id} block={block} />
            if (block.type === 'artifact')
              return <ArtifactBlock key={block.id} block={block} />
            return (
              <ThinkBlock
                key={block.id}
                block={block}
                live={streaming && block.id === lastThinkId}
              />
            )
          })}
        </div>

        {message.content && (
          <div className="msg-content">
            <Markdown content={message.content} />
            {streaming && <span className="msg-cursor" />}
          </div>
        )}

        {streaming && !message.content && (
          <div className="msg-thinking">
            <span className="msg-thinking-dot" />
            <span className="msg-thinking-dot" />
            <span className="msg-thinking-dot" />
            <span className="msg-thinking-text">正在组织回答…</span>
          </div>
        )}

        {message.status === 'stopped' && (
          <div className="msg-status-tag">已停止生成</div>
        )}

        {message.status === 'error' && (
          <Alert
            className="msg-error"
            type="error"
            showIcon
            icon={<ExclamationCircleFilled />}
            message={message.error_text ?? '运行失败'}
            action={
              <Button size="small" icon={<ReloadOutlined />} onClick={onRetry}>
                重试
              </Button>
            }
          />
        )}
      </div>
    </div>
  )
}
