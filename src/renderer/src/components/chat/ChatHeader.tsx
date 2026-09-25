import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  ExclamationCircleFilled,
  LoadingOutlined,
  PauseCircleFilled,
} from '@ant-design/icons'
import { useEffect, useRef, useState } from 'react'
import type { TaskStatus } from '../../types/api'
import { formatTokens } from '../../lib/format'

interface Props {
  title: string
  status: TaskStatus
  totalTokens: number | null
  onRename: (title: string) => Promise<void>
}

const STATUS_META: Record<TaskStatus, { label: string; className: string; icon?: JSX.Element }> = {
  idle: { label: '空闲', className: 'idle' },
  running: { label: '处理中', className: 'running', icon: <LoadingOutlined spin /> },
  stopped: { label: '已停止', className: 'stopped', icon: <PauseCircleFilled /> },
  error: { label: '出错', className: 'error', icon: <ExclamationCircleFilled /> },
  done: { label: '已完成', className: 'done', icon: <CheckOutlined /> },
}

export default function ChatHeader({ title, status, totalTokens, onRename }: Props) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(title)
  const inputRef = useRef<HTMLInputElement>(null)
  const meta = STATUS_META[status]

  useEffect(() => {
    if (!editing) setValue(title)
  }, [title, editing])

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  const commit = async () => {
    const next = value.trim()
    setEditing(false)
    if (next && next !== title) await onRename(next).catch(() => undefined)
    else setValue(title)
  }

  return (
    <header className="chat-header">
      <div className="chat-header-title-wrap">
        {editing ? (
          <div className="chat-title-edit">
            <input
              ref={inputRef}
              className="chat-title-input"
              value={value}
              maxLength={200}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void commit()
                if (e.key === 'Escape') {
                  setValue(title)
                  setEditing(false)
                }
              }}
            />
            <button type="button" className="chat-title-btn ok" onClick={() => void commit()}>
              <CheckOutlined />
            </button>
            <button
              type="button"
              className="chat-title-btn"
              onClick={() => {
                setValue(title)
                setEditing(false)
              }}
            >
              <CloseOutlined />
            </button>
          </div>
        ) : (
          <button type="button" className="chat-title" onClick={() => setEditing(true)}>
            <span className="chat-title-text">{title}</span>
            <EditOutlined className="chat-title-edit-ic" />
          </button>
        )}
      </div>
      <div className="chat-header-right">
        {status !== 'idle' && (
          <span className={`chat-status-tag ${meta.className}`}>
            {meta.icon}
            {meta.label}
          </span>
        )}
        {totalTokens !== null && totalTokens > 0 && (
          <span className="chat-usage-tag" title="本轮及历史累计 Token 用量">
            {formatTokens(totalTokens)} tokens
          </span>
        )}
      </div>
    </header>
  )
}
