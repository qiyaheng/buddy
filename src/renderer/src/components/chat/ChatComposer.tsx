import {
  PaperClipOutlined,
  SendOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { Tooltip } from 'antd'
import { useEffect, useLayoutEffect, useRef } from 'react'

interface Props {
  draft: string
  running: boolean
  modelName: string | null
  onChange: (text: string) => void
  onSend: () => void
  onStop: () => void
}

const MAX_AUTO_HEIGHT = 168

export default function ChatComposer({
  draft,
  running,
  modelName,
  onChange,
  onSend,
  onStop,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const composing = useRef(false)

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_AUTO_HEIGHT)}px`
  }, [draft])

  useEffect(() => {
    if (!running) ref.current?.focus()
  }, [running])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !composing.current) {
      e.preventDefault()
      if (!running && draft.trim()) onSend()
    }
  }

  return (
    <div className="composer-wrap">
      <div className={`composer ${running ? 'is-running' : ''}`}>
        <textarea
          ref={ref}
          className="composer-input"
          placeholder={running ? '专家正在执行任务…' : '输入任务，Enter 发送 / Shift+Enter 换行'}
          value={draft}
          rows={1}
          disabled={running}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => {
            composing.current = true
          }}
          onCompositionEnd={() => {
            composing.current = false
          }}
        />
        <div className="composer-bar">
          <div className="composer-tools">
            <Tooltip title="附件功能即将上线" placement="top">
              <button type="button" className="composer-chip" disabled>
                <PaperClipOutlined />
                <span>附件</span>
              </button>
            </Tooltip>
            <Tooltip title="模型切换将在后续版本开放" placement="top">
              <button type="button" className="composer-chip" disabled>
                <ThunderboltOutlined />
                <span>{modelName ?? '默认模型'}</span>
              </button>
            </Tooltip>
          </div>
          {running ? (
            <button type="button" className="composer-stop" onClick={onStop}>
              <StopOutlined />
              <span>停止生成</span>
            </button>
          ) : (
            <button
              type="button"
              className="composer-send"
              disabled={!draft.trim()}
              onClick={onSend}
              aria-label="发送"
            >
              <SendOutlined />
            </button>
          )}
        </div>
      </div>
      <div className="composer-hint">内容由 AI 生成，请核对关键信息</div>
    </div>
  )
}
