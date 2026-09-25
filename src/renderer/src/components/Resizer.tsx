import { useCallback, useEffect, useRef } from 'react'

interface ResizerProps {
  /** 拖拽中持续回调，参数为当前鼠标 clientX（绝对坐标，由父级换算栏宽） */
  onDrag: (clientX: number) => void
}

export default function Resizer({ onDrag }: ResizerProps) {
  const dragging = useRef(false)

  const handleMouseMove = useCallback(
    (event: MouseEvent) => {
      if (dragging.current) onDrag(event.clientX)
    },
    [onDrag],
  )

  const handleMouseUp = useCallback(() => {
    dragging.current = false
    document.body.classList.remove('wb-resizing')
  }, [])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  return (
    <div
      className="wb-resizer"
      onMouseDown={(event) => {
        dragging.current = true
        document.body.classList.add('wb-resizing')
        event.preventDefault()
      }}
    />
  )
}
