import { VerticalAlignBottomOutlined } from '@ant-design/icons'
import { useLayoutEffect, useRef, useState } from 'react'
import type { ExpertSnapshot } from '../../types/api'
import type { UIMessage } from '../../types/chat'
import AgentMessage from './AgentMessage'

interface Props {
  messages: UIMessage[]
  expert: ExpertSnapshot | null
  onRetry: () => void
}

export default function MessageList({ messages, expert, onRetry }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const [showJump, setShowJump] = useState(false)

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
    stickToBottom.current = atBottom
    setShowJump(!atBottom)
  }

  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [messages])

  const jumpToBottom = () => {
    const el = scrollRef.current
    if (!el) return
    stickToBottom.current = true
    setShowJump(false)
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }

  return (
    <div className="msg-scroll" ref={scrollRef} onScroll={handleScroll}>
      <div className="msg-list-inner">
        {messages.map((m) =>
          m.role === 'user' ? (
            <div className="msg msg-user" key={m.id}>
              <div className="msg-user-bubble">{m.content}</div>
            </div>
          ) : (
            <AgentMessage key={m.id} message={m} expert={expert} onRetry={onRetry} />
          ),
        )}
      </div>
      {showJump && (
        <button type="button" className="msg-jump-bottom" onClick={jumpToBottom}>
          <VerticalAlignBottomOutlined />
          回到底部
        </button>
      )}
    </div>
  )
}
