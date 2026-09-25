import {
  App as AntdApp,
  Dropdown,
  Input,
  type InputRef,
  type MenuProps,
} from 'antd'
import {
  AppstoreOutlined,
  CheckOutlined,
  DeleteOutlined,
  EditOutlined,
  ExclamationCircleFilled,
  FileDoneOutlined,
  FolderOpenFilled,
  FolderOutlined,
  InboxOutlined,
  MessageOutlined,
  MoreOutlined,
  PlusOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'
import { formatTime } from '../lib/format'
import { useChatStore } from '../stores/chat-store'
import { useTasksStore, type SidebarFilter } from '../stores/tasks-store'
import type { Folder, TaskStatus, TaskSummary } from '../types/api'

/* ---------------- 行内编辑输入框 ---------------- */

function InlineEdit({
  initial,
  placeholder,
  onSubmit,
  onCancel,
}: {
  initial: string
  placeholder: string
  onSubmit: (value: string) => void
  onCancel: () => void
}) {
  const [value, setValue] = useState(initial)
  const ref = useRef<InputRef>(null)
  useEffect(() => {
    ref.current?.focus({ cursor: 'all' })
  }, [])
  return (
    <Input
      ref={ref}
      size="small"
      autoFocus
      value={value}
      placeholder={placeholder}
      onChange={(e) => setValue(e.target.value)}
      onPressEnter={() => onSubmit(value)}
      onBlur={() => onSubmit(value)}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.stopPropagation()
          onCancel()
        }
      }}
      className="wb-inline-input"
    />
  )
}

/* ---------------- 状态指示点 ---------------- */

function StatusDot({ status }: { status: TaskStatus }) {
  if (status === 'running') return <span className="wb-task-dot running" title="运行中" />
  if (status === 'error') return <span className="wb-task-dot error" title="出错" />
  if (status === 'stopped') return <span className="wb-task-dot stopped" title="已停止" />
  return null
}

/* ---------------- 任务行 ---------------- */

function TaskRow({
  task,
  active,
  folders,
  onRename,
  onMove,
  onDelete,
}: {
  task: TaskSummary
  active: boolean
  folders: Folder[]
  onRename: (title: string) => void
  onMove: (folderId: string | null) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)

  const menuItems: MenuProps['items'] = [
    { key: 'rename', icon: <EditOutlined />, label: '重命名' },
    { type: 'divider' },
    {
      key: 'menu-move',
      icon: <FolderOutlined />,
      label: '移动到',
      children: [
        {
          key: 'move:none',
          label: (
            <span className="wb-move-label">
              未分组
              {task.folder_id === null && <CheckOutlined className="wb-move-check" />}
            </span>
          ),
        },
        ...folders.map((f) => ({
          key: `move:${f.id}`,
          label: (
            <span className="wb-move-label">
              {f.name}
              {task.folder_id === f.id && <CheckOutlined className="wb-move-check" />}
            </span>
          ),
        })),
      ],
    },
    { type: 'divider' },
    { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true },
  ]

  const onMenuClick: MenuProps['onClick'] = ({ key, domEvent }) => {
    domEvent.stopPropagation()
    if (key === 'rename') setEditing(true)
    else if (key === 'delete') onDelete()
    else if (key === 'move:none') onMove(null)
    else if (key.startsWith('move:')) onMove(key.slice(5))
  }

  return (
    <div className={`wb-task-item${active ? ' active' : ''}`}>
      {editing ? (
        <div onClick={(e) => e.stopPropagation()}>
          <InlineEdit
            initial={task.title}
            placeholder="任务名称"
            onSubmit={(v) => {
              setEditing(false)
              if (v.trim() && v.trim() !== task.title) onRename(v.trim())
            }}
            onCancel={() => setEditing(false)}
          />
        </div>
      ) : (
        <>
          <StatusDot status={task.status} />
          <span className="wb-task-name">{task.title || '未命名任务'}</span>
          <span className="wb-task-time">{formatTime(task.last_message_at ?? task.updated_at)}</span>
          <Dropdown
            trigger={['click']}
            menu={{ items: menuItems, onClick: onMenuClick }}
            placement="bottomRight"
          >
            <button
              type="button"
              className="wb-task-more"
              onClick={(e) => e.stopPropagation()}
              aria-label="任务操作"
            >
              <MoreOutlined />
            </button>
          </Dropdown>
        </>
      )}
    </div>
  )
}

/* ---------------- 侧边栏主体 ---------------- */

export default function Sidebar() {
  const navigate = useNavigate()
  const { taskId: activeTaskId } = useParams<{ taskId?: string }>()
  const { modal, message } = AntdApp.useApp()

  const {
    tasks,
    folders,
    filter,
    query,
    refresh,
    setFilter,
    setQuery,
    renameTask,
    moveTask,
    removeTask,
    createFolder,
    renameFolder,
    removeFolder,
  } = useTasksStore()

  const [editingFolder, setEditingFolder] = useState<string | null>(null)
  const [creatingFolder, setCreatingFolder] = useState(false)

  // 首次加载 + 轮询（仅有运行中任务时才请求）
  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => {
      if (useTasksStore.getState().tasks.some((t) => t.status === 'running')) void refresh()
    }, 4000)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 搜索 debounce
  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 280)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const ungroupedCount = tasks.filter((t) => t.folder_id === null).length
  const countOf = (id: string) => tasks.filter((t) => t.folder_id === id).length

  const visibleTasks = tasks.filter((t) => {
    if (filter === 'all' || filter === 'search') return true
    if (filter === 'ungrouped') return t.folder_id === null
    return t.folder_id === filter.slice('folder:'.length)
  })

  const confirmDeleteTask = (task: TaskSummary) => {
    modal.confirm({
      title: '删除任务',
      icon: <ExclamationCircleFilled />,
      content: `将删除任务「${task.title}」及其全部消息与产物文件，删除后不可恢复。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await removeTask(task.id)
        message.success('任务已删除')
        if (activeTaskId === task.id) navigate('/chat')
      },
    })
  }

  const confirmDeleteFolder = (folder: Folder) => {
    modal.confirm({
      title: '删除文件夹',
      icon: <ExclamationCircleFilled />,
      content: `将删除文件夹「${folder.name}」，其中的任务会移动到「未分组」，任务本身不会被删除。`,
      okText: '删除文件夹',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => removeFolder(folder.id),
    })
  }

  const renderFolderRow = (folder: Folder) => {
    const key: SidebarFilter = `folder:${folder.id}`
    const selected = filter === key
    if (editingFolder === folder.id) {
      return (
        <div key={folder.id} className="wb-group-row editing">
          <InlineEdit
            initial={folder.name}
            placeholder="文件夹名称"
            onSubmit={(v) => {
              setEditingFolder(null)
              if (v.trim() && v.trim() !== folder.name) void renameFolder(folder.id, v.trim())
            }}
            onCancel={() => setEditingFolder(null)}
          />
        </div>
      )
    }
    return (
      <div
        key={folder.id}
        className={`wb-group-row${selected ? ' active' : ''}`}
        onClick={() => setFilter(key)}
      >
        {selected ? <FolderOpenFilled className="wb-group-ic" /> : <FolderOutlined className="wb-group-ic" />}
        <span className="wb-group-name">{folder.name}</span>
        <span className="wb-group-count">{countOf(folder.id)}</span>
        <span className="wb-group-actions">
          <button
            type="button"
            className="wb-group-act"
            title="重命名"
            onClick={(e) => {
              e.stopPropagation()
              setEditingFolder(folder.id)
            }}
          >
            <EditOutlined />
          </button>
          <button
            type="button"
            className="wb-group-act danger"
            title="删除文件夹"
            onClick={(e) => {
              e.stopPropagation()
              confirmDeleteFolder(folder)
            }}
          >
            <DeleteOutlined />
          </button>
        </span>
      </div>
    )
  }

  return (
    <div className="wb-sidebar-inner">
      <div className="wb-brand">
        <div className="wb-brand-logo">S</div>
        <div className="wb-brand-text">
          <div className="wb-brand-name">SMEbuddy</div>
          <div className="wb-brand-sub">AI 智能工作台</div>
        </div>
      </div>

      <button className="wb-new-task" onClick={() => navigate('/chat')}>
        <PlusOutlined />
        <span>新建任务</span>
      </button>

      <nav className="wb-nav">
        <NavLink to="/chat" className="wb-nav-item">
          <MessageOutlined className="wb-nav-icon" />
          <span>任务台</span>
        </NavLink>
        <NavLink to="/experts" className="wb-nav-item">
          <AppstoreOutlined className="wb-nav-icon" />
          <span>专家广场</span>
        </NavLink>
      </nav>

      <div className="wb-search-wrap">
        <Input
          allowClear
          size="small"
          prefix={<SearchOutlined className="wb-search-ic" />}
          placeholder="搜索任务或消息"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="wb-task-area">
        {filter === 'search' ? (
          <>
            <div className="wb-section-label">
              搜索结果{tasks.length > 0 ? ` · ${tasks.length}` : ''}
            </div>
            {visibleTasks.length === 0 && <div className="wb-empty-mini">没有匹配的任务</div>}
          </>
        ) : (
          <>
            <div className="wb-group-list">
              <div
                className={`wb-group-row${filter === 'all' ? ' active' : ''}`}
                onClick={() => setFilter('all')}
              >
                <FileDoneOutlined className="wb-group-ic" />
                <span className="wb-group-name">全部任务</span>
                <span className="wb-group-count">{tasks.length}</span>
              </div>
              <div
                className={`wb-group-row${filter === 'ungrouped' ? ' active' : ''}`}
                onClick={() => setFilter('ungrouped')}
              >
                <InboxOutlined className="wb-group-ic" />
                <span className="wb-group-name">未分组</span>
                <span className="wb-group-count">{ungroupedCount}</span>
              </div>
              {folders.map(renderFolderRow)}
            </div>
            {creatingFolder && (
              <div className="wb-group-row editing">
                <InlineEdit
                  initial=""
                  placeholder="文件夹名称"
                  onSubmit={(v) => {
                    setCreatingFolder(false)
                    if (v.trim()) void createFolder(v.trim())
                  }}
                  onCancel={() => setCreatingFolder(false)}
                />
              </div>
            )}
            <button
              type="button"
              className="wb-folder-add"
              onClick={() => setCreatingFolder(true)}
            >
              <PlusOutlined />
              新建文件夹
            </button>
          </>
        )}

        <div className="wb-task-list">
          {visibleTasks.map((task) => (
            <div key={task.id} onClick={() => navigate(`/chat/${task.id}`)}>
              <TaskRow
                task={task}
                active={activeTaskId === task.id}
                folders={folders}
                onRename={(title) =>
                  renameTask(task.id, title).then(() => {
                    // 同步对话页标题栏（两个 store 各持一份任务快照）
                    useChatStore.setState((s) =>
                      s.task?.id === task.id ? { task: { ...s.task, title } } : {},
                    )
                  })
                }
                onMove={(folderId) => void moveTask(task.id, folderId)}
                onDelete={() => confirmDeleteTask(task)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="wb-sidebar-footer">
        <NavLink to="/settings" className="wb-nav-item wb-footer-item">
          <SettingOutlined className="wb-nav-icon" />
          <span>设置</span>
        </NavLink>
        <div className="wb-user">
          <div className="wb-avatar">S</div>
          <div className="wb-user-meta">
            <div className="wb-user-name">本地用户</div>
            <div className="wb-user-desc">数据仅保存在本机</div>
          </div>
        </div>
      </div>
    </div>
  )
}
