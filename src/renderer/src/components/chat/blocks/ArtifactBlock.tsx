import {
  FileExcelOutlined,
  FileMarkdownOutlined,
  FileOutlined,
  FilePptOutlined,
  FileWordOutlined,
} from '@ant-design/icons'
import { formatBytes } from '../../../lib/format'
import type { ArtifactBlock as ArtifactBlockType } from '../../../types/chat'

function formatIcon(fmt: string) {
  switch (fmt) {
    case 'md':
      return <FileMarkdownOutlined style={{ color: '#4f7cff' }} />
    case 'docx':
      return <FileWordOutlined style={{ color: '#2b7cd3' }} />
    case 'pptx':
      return <FilePptOutlined style={{ color: '#f97316' }} />
    case 'xlsx':
      return <FileExcelOutlined style={{ color: '#16a34a' }} />
    default:
      return <FileOutlined />
  }
}

export default function ArtifactBlock({ block }: { block: ArtifactBlockType }) {
  return (
    <div className="block-artifact" title="产物已生成，可在右侧产物面板查看与导出">
      <span className="block-artifact-icon">{formatIcon(block.format)}</span>
      <span className="block-artifact-main">
        <span className="block-artifact-name">{block.filename}</span>
        <span className="block-artifact-meta">
          {block.format.toUpperCase()} · {formatBytes(block.size_bytes)}
        </span>
      </span>
    </div>
  )
}
