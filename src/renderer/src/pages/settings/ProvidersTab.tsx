import {
  ApiOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  DeleteOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  StarFilled,
} from '@ant-design/icons'
import { Alert, App, Button, Empty, Popconfirm, Tag, Tooltip } from 'antd'
import { useState } from 'react'
import { useConfigStore } from '../../stores/config-store'
import { useAppStore } from '../../stores/app-store'
import type { ConnectionTestResult, ModelConfig, Provider } from '../../types/api'
import ModelFormModal from './ModelFormModal'
import ProviderFormModal from './ProviderFormModal'

interface TestState {
  loading: boolean
  result: ConnectionTestResult | null
}

export default function ProvidersTab() {
  const { providers, deleteProvider, deleteModel, testConnection } = useConfigStore()
  const refreshSetup = useAppStore((s) => s.refreshSetup)
  const { message } = App.useApp()

  const [providerModal, setProviderModal] = useState<{ open: boolean; provider: Provider | null }>({
    open: false,
    provider: null,
  })
  const [modelModal, setModelModal] = useState<{
    open: boolean
    provider: Provider | null
    model: ModelConfig | null
  }>({ open: false, provider: null, model: null })
  const [tests, setTests] = useState<Record<string, TestState>>({})

  const runTest = async (provider: Provider, modelId?: string) => {
    setTests((prev) => ({ ...prev, [provider.id]: { loading: true, result: null } }))
    try {
      const result = await testConnection(provider.id, modelId)
      setTests((prev) => ({ ...prev, [provider.id]: { loading: false, result } }))
    } catch (err) {
      setTests((prev) => ({
        ...prev,
        [provider.id]: {
          loading: false,
          result: { ok: false, code: 'request_failed', message: err instanceof Error ? err.message : '请求失败' },
        },
      }))
    }
  }

  const handleDeleteProvider = async (provider: Provider) => {
    await deleteProvider(provider.id)
    await refreshSetup()
    message.success('服务商已删除')
  }

  const handleDeleteModel = async (model: ModelConfig) => {
    await deleteModel(model.id)
    await refreshSetup()
    message.success('模型已删除')
  }

  const defaultModel = (provider: Provider) =>
    provider.models.find((m) => m.is_default) ?? provider.models[0]

  return (
    <div className="settings-pane">
      <div className="settings-pane-head">
        <p className="settings-section-desc" style={{ margin: 0 }}>
          配置 OpenAI 兼容的模型服务，支持添加多个服务商与模型。
        </p>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setProviderModal({ open: true, provider: null })}
        >
          添加服务商
        </Button>
      </div>

      {providers.length === 0 && (
        <Empty
          description="还没有模型服务商"
          style={{ padding: '40px 0' }}
        >
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setProviderModal({ open: true, provider: null })}
          >
            添加第一个服务商
          </Button>
        </Empty>
      )}

      <div className="provider-list">
        {providers.map((provider) => {
          const test = tests[provider.id]
          return (
            <div className={`provider-card ${provider.enabled ? '' : 'is-disabled'}`} key={provider.id}>
              <div className="provider-card-head">
                <div className="provider-title">
                  <span className="provider-name">{provider.name}</span>
                  <Tag color={provider.enabled ? 'green' : 'default'}>
                    {provider.enabled ? '已启用' : '已停用'}
                  </Tag>
                </div>
                <div className="provider-actions">
                  <Tooltip title="测试连接（默认模型）">
                    <Button
                      size="small"
                      icon={<ApiOutlined />}
                      loading={test?.loading}
                      disabled={provider.models.length === 0}
                      onClick={() => void runTest(provider, defaultModel(provider)?.model_id)}
                    >
                      测试连接
                    </Button>
                  </Tooltip>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => setProviderModal({ open: true, provider })}
                  >
                    编辑
                  </Button>
                  <Popconfirm
                    title="删除服务商"
                    description="将同时删除其下所有模型配置，确认删除？"
                    okText="删除"
                    okButtonProps={{ danger: true }}
                    cancelText="取消"
                    onConfirm={() => void handleDeleteProvider(provider)}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </div>
              </div>

              <div className="provider-meta">
                <code className="settings-mono">{provider.base_url}</code>
                <span className="provider-meta-sep">·</span>
                <span>
                  密钥：
                  {provider.has_api_key ? (
                    <span className="key-masked">{provider.api_key_masked}</span>
                  ) : (
                    <span className="key-missing">未配置</span>
                  )}
                </span>
                <span className="provider-meta-sep">·</span>
                <span>超时 {provider.timeout_seconds}s</span>
              </div>

              <div className="model-list">
                {provider.models.map((model) => (
                  <div className="model-row" key={model.id}>
                    <div className="model-row-main">
                      <span className="model-display-name">
                        {model.is_default && (
                          <StarFilled style={{ color: '#f5a623', marginRight: 6 }} />
                        )}
                        {model.display_name}
                      </span>
                      <code className="settings-mono model-id">{model.model_id}</code>
                      <span className="model-capabilities">
                        {model.capabilities.map((cap) => (
                          <Tag key={cap} bordered={false} className="cap-tag">
                            {cap}
                          </Tag>
                        ))}
                      </span>
                    </div>
                    <div className="model-row-actions">
                      <Button
                        type="link"
                        size="small"
                        onClick={() => void runTest(provider, model.model_id)}
                      >
                        测试
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        onClick={() => setModelModal({ open: true, provider, model })}
                      >
                        编辑
                      </Button>
                      <Popconfirm
                        title="删除模型"
                        description={`确认删除模型「${model.display_name}」？`}
                        okText="删除"
                        okButtonProps={{ danger: true }}
                        cancelText="取消"
                        onConfirm={() => void handleDeleteModel(model)}
                      >
                        <Button type="link" size="small" danger>
                          删除
                        </Button>
                      </Popconfirm>
                    </div>
                  </div>
                ))}
                <Button
                  type="dashed"
                  size="small"
                  icon={<PlusOutlined />}
                  className="model-add-btn"
                  onClick={() => setModelModal({ open: true, provider, model: null })}
                >
                  添加模型
                </Button>
              </div>

              {test?.result && (
                <Alert
                  className="provider-test-alert"
                  type={test.result.ok ? 'success' : 'error'}
                  showIcon
                  icon={
                    test.result.ok ? (
                      <CheckCircleFilled />
                    ) : test.result.code === 'auth_failed' ? (
                      <ExclamationCircleOutlined />
                    ) : (
                      <CloseCircleFilled />
                    )
                  }
                  message={
                    test.result.ok
                      ? `连接成功${test.result.message ? `：${test.result.message}` : ''}`
                      : `连接失败（${test.result.code}）：${test.result.message}`
                  }
                />
              )}
            </div>
          )
        })}
      </div>

      <ProviderFormModal
        open={providerModal.open}
        provider={providerModal.provider}
        onClose={() => setProviderModal({ open: false, provider: null })}
      />
      {modelModal.open && modelModal.provider && (
        <ModelFormModal
          open
          provider={modelModal.provider}
          model={modelModal.model}
          onClose={() => setModelModal({ open: false, provider: null, model: null })}
        />
      )}
    </div>
  )
}
