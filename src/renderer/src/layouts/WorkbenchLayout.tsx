import { DoubleLeftOutlined } from '@ant-design/icons'
import { Tooltip } from 'antd'
import { Outlet, useLocation } from 'react-router-dom'
import Resizer from '../components/Resizer'
import ResultPanel from '../components/ResultPanel'
import Sidebar from '../components/Sidebar'
import { useAppStore } from '../stores/app-store'

export default function WorkbenchLayout() {
  const location = useLocation()
  const { leftWidth, rightWidth, rightCollapsed, setLeftWidth, setRightWidth, toggleRightCollapsed } =
    useAppStore()
  const isChat = location.pathname.startsWith('/chat')
  const showResult = isChat && !rightCollapsed

  return (
    <div className="workbench">
      <aside className="wb-sidebar" style={{ width: leftWidth }}>
        <Sidebar />
      </aside>
      <Resizer onDrag={(clientX) => setLeftWidth(clientX)} />
      <main className="wb-main">
        <Outlet />
        {isChat && rightCollapsed && (
          <Tooltip title="展开产物面板" placement="left">
            <button
              className="wb-result-expand"
              onClick={toggleRightCollapsed}
              aria-label="展开产物面板"
            >
              <DoubleLeftOutlined />
            </button>
          </Tooltip>
        )}
      </main>
      {showResult && (
        <>
          <Resizer onDrag={(clientX) => setRightWidth(window.innerWidth - clientX)} />
          <section className="wb-result" style={{ width: rightWidth }}>
            <ResultPanel />
          </section>
        </>
      )}
    </div>
  )
}
