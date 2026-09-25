import { ArrowRightOutlined, CloseCircleFilled } from '@ant-design/icons'
import { Alert, Button } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import ChatComposer, { type ModelOption } from '../components/chat/ChatComposer'
import ChatHeader from '../components/chat/ChatHeader'
import ChatWelcome from '../components/chat/ChatWelcome'
import MessageList from '../components/chat/MessageList'
import { http } from '../lib/http'
import { useAppStore } from '../stores/app-store'
import { useChatStore } from '../stores/chat-store'
import type { Provider } from '../types/api'

function SetupGuide() {
  const navigate = useNavigate()
  return (
    <div className="chat-page">
      <div className="chat-welcome">
        <div className="chat-hero-logo">S</div>
        <h1 className="chat-hero-title">配置你的第一个模型，开始指挥专家团</h1>
        <p className="chat-hero-sub">
          支持任意 OpenAI 兼容接口（OpenAI、DeepSeek、本地 Ollama 等）。
          <br />
          凭证仅保存在本机，不上报任何服务器。
        </p>
        <Button type="primary" size="large" onClick={() => navigate('/settings')}>
          去配置模型
          <ArrowRightOutlined />
        </Button>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const hasModels = useAppStore((s) => s.hasModels)
  const defaultModelName = useAppStore((s) => s.defaultModelName)
  const navigate = useNavigate()
  const { taskId } = useParams<{ taskId?: string }>()

  const {
    task,
    messages,
    running,
    draft,
    notice,
    usage,
    selectedModelId,
    setDraft,
    setSelectedModelId,
    startBlank,
    loadTask,
    send,
    stop,
    retryLast,
    renameTask,
    clearNotice,
  } = useChatStore()

  const [models, setModels] = useState<ModelOption[]>([])

  useEffect(() => {
    if (!hasModels) return
    http
      .get<Provider[]>('/api/providers')
      .then((providers) => {
        setModels(
          providers
            .filter((p) => p.enabled)
            .flatMap((p) =>
              p.models.map((m) => ({
                id: m.id,
                displayName: m.display_name,
                providerName: p.name,
              })),
            ),
        )
      })
      .catch(() => setModels([]))
  }, [hasModels])

  useEffect(() => {
    if (taskId) void loadTask(taskId)
    else startBlank()
    // 仅随路由任务切换触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId])

  // chip 上展示的模型名：选中模型 > 任务绑定模型 > 全局默认
  const currentModelName = useMemo(() => {
    if (selectedModelId) {
      const m = models.find((x) => x.id === selectedModelId)
      if (m) return m.displayName
    }
    return task?.model_snapshot?.display_name ?? defaultModelName
  }, [selectedModelId, models, task, defaultModelName])

  if (!hasModels) return <SetupGuide />

  const isBlank = !taskId && messages.length === 0

  return (
    <div className="chat-shell">
      {task && (
        <ChatHeader
          title={task.title}
          status={running ? 'running' : task.status}
          totalTokens={usage?.total_tokens ?? null}
          onRename={renameTask}
        />
      )}

      {isBlank ? (
        <div className="msg-scroll msg-scroll-welcome">
          <ChatWelcome onPick={(prompt) => void send(prompt, navigate)} />
        </div>
      ) : (
        <MessageList
          messages={messages}
          expert={task?.expert_snapshot ?? null}
          onRetry={() => void retryLast()}
        />
      )}

      {notice && (
        <div className="chat-notice">
          <Alert
            type="error"
            showIcon
            icon={<CloseCircleFilled />}
            message={notice}
            closable
            onClose={clearNotice}
          />
        </div>
      )}

      <ChatComposer
        draft={draft}
        running={running}
        modelName={currentModelName}
        models={models}
        selectedModelId={selectedModelId}
        onSelectModel={setSelectedModelId}
        onChange={setDraft}
        onSend={() => void send(draft, navigate)}
        onStop={() => void stop()}
      />
    </div>
  )
}
