import {
  CheckCircleFilled,
  CloseCircleFilled,
  DownOutlined,
  GlobalOutlined,
  LoadingOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import type { ToolBlock as ToolBlockType } from '../../../types/chat'

const TOOL_NAME_MAP: Record<string, string> = {
  web_search: '联网搜索',
  web_fetch: '读取网页',
}

function toolIcon(name: string) {
  if (name === 'web_search' || name === 'web_fetch') return <GlobalOutlined />
  return <ToolOutlined />
}

function openExternal(href: string) {
  const wb = (window as unknown as { wb?: { openExternal?: (u: string) => void } }).wb
  if (wb?.openExternal) wb.openExternal(href)
  else window.open(href, '_blank', 'noopener')
}

export default function ToolBlock({ block }: { block: ToolBlockType }) {
  const [open, setOpen] = useState(false)
  const running = block.status === 'started'
  const failed = block.status === 'error'
  const displayName = TOOL_NAME_MAP[block.name] ?? block.name
  const hasDetail =
    !!block.input_summary ||
    !!block.summary ||
    (block.sources !== undefined && block.sources.length > 0)

  return (
    <div className={`block-tool ${running ? 'is-running' : ''} ${failed ? 'is-error' : ''}`}>
      <button
        type="button"
        className="block-tool-header"
        onClick={() => hasDetail && setOpen((v) => !v)}
        disabled={!hasDetail}
      >
        <span className={`block-tool-icon ${failed ? 'is-error' : ''}`}>
          {running ? <LoadingOutlined spin /> : failed ? <CloseCircleFilled /> : toolIcon(block.name)}
        </span>
        <span className="block-tool-name">{displayName}</span>
        {running ? (
          <span className="block-tool-state">正在执行…</span>
        ) : failed ? (
          <span className="block-tool-state is-error">执行失败</span>
        ) : (
          <span className="block-tool-meta">
            {block.elapsed_ms !== undefined && <span>{block.elapsed_ms} ms</span>}
            <CheckCircleFilled className="block-tool-ok" />
          </span>
        )}
        {hasDetail && <DownOutlined className={`block-tool-chevron ${open ? 'is-open' : ''}`} />}
      </button>

      {open && (
        <div className="block-tool-detail">
          {block.input_summary && <div className="tool-detail-row">▸ {block.input_summary}</div>}
          {block.summary && <div className="tool-detail-row tool-detail-summary">{block.summary}</div>}
          {block.sources && block.sources.length > 0 && (
            <div className="tool-sources">
              {block.sources.map((src) => (
                <a
                  key={src.url}
                  className="tool-source"
                  href={src.url}
                  onClick={(e) => {
                    e.preventDefault()
                    openExternal(src.url)
                  }}
                >
                  <span className="tool-source-title">{src.title}</span>
                  <span className="tool-source-url">{src.url}</span>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
