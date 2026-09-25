import { DownOutlined, LoadingOutlined } from '@ant-design/icons'
import { useEffect, useRef, useState } from 'react'
import type { ThinkBlock as ThinkBlockType } from '../../../types/chat'

export default function ThinkBlock({ block, live }: { block: ThinkBlockType; live: boolean }) {
  const [open, setOpen] = useState(live)
  const prevLive = useRef(live)

  // 生成结束后自动收起（用户在生成期间的手动折叠不受影响，仅沿变化触发一次）
  useEffect(() => {
    if (prevLive.current && !live) setOpen(false)
    prevLive.current = live
  }, [live])

  return (
    <div className={`block-think ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="block-think-header"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="block-think-title">
          {live ? <LoadingOutlined className="think-spin" /> : <span className="think-dot" />}
          思考过程
        </span>
        <DownOutlined className="block-think-chevron" />
      </button>
      <div className="block-think-wrap">
        <div className="block-think-body">
          <div className="block-think-text">{block.text}</div>
        </div>
      </div>
    </div>
  )
}
