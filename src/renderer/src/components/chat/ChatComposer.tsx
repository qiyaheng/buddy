import {
  CheckOutlined,
  DownOutlined,
  PaperClipOutlined,
  SendOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { Dropdown, Tooltip } from 'antd'
import { useEffect, useLayoutEffect, useRef } from 'react'

export interface ModelOption {
  /** ModelConfig 主键 */
  id: string
  displayName: string
  providerName: string
}

interface Props {
  draft: string
  running: boolean
  modelName: string | null
  models: ModelOption[]
  selectedModelId: string | null
  onSelectModel: (id: string | null) => void
  onChange: (text: string) => void
  onSend: () => void
  onStop: () => void
}

const MAX_AUTO_HEIGHT = 168

export default function ChatComposer({
  draft,
  running,
  modelName,
  models,
  selectedModelId,
  onSelectModel,
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
            <Dropdown
              trigger={['click']}
              disabled={running || models.length === 0}
              menu={{
                selectable: true,
                selectedKeys: selectedModelId ? [selectedModelId] : [],
                items: models.map((m) => ({
                  key: m.id,
                  icon: selectedModelId === m.id ? <CheckOutlined /> : undefined,
                  label: (
                    <span>
                      {m.displayName}
                      <span className="model-option-provider"> · {m.providerName}</span>
                    </span>
                  ),
                })),
                onClick: ({ key }) => onSelectModel(key),
              }}
            >
              <button type="button" className="composer-chip" disabled={running}>
                <ThunderboltOutlined />
                <span>{modelName ?? '默认模型'}</span>
                <DownOutlined style={{ fontSize: 10 }} />
              </button>
            </Dropdown>
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
