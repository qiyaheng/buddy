import { App, Form, Input, InputNumber, Modal, Switch } from 'antd'
import { useEffect, useState } from 'react'
import { useConfigStore } from '../../stores/config-store'
import { useAppStore } from '../../stores/app-store'
import type { Provider, ProviderFormModel } from '../../types/api'

interface Props {
  open: boolean
  provider: Provider | null
  onClose: () => void
}

interface FormValues {
  name: string
  base_url: string
  api_key: string
  timeout_seconds: number
  enabled: boolean
}

export default function ProviderFormModal({ open, provider, onClose }: Props) {
  const isEdit = Boolean(provider)
  const { createProvider, updateProvider } = useConfigStore()
  const refreshSetup = useAppStore((s) => s.refreshSetup)
  const { message } = App.useApp()
  const [form] = Form.useForm<FormValues>()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        name: provider?.name ?? '',
        base_url: provider?.base_url ?? '',
        api_key: '',
        timeout_seconds: provider?.timeout_seconds ?? 60,
        enabled: provider?.enabled ?? true,
      })
    }
  }, [open, provider, form])

  const handleOk = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (provider) {
        await updateProvider(provider.id, {
          name: values.name.trim(),
          base_url: values.base_url.trim(),
          api_key: values.api_key ? values.api_key.trim() : null,
          timeout_seconds: values.timeout_seconds,
          enabled: values.enabled,
        })
        message.success('服务商已更新')
      } else {
        // 新建时暂不携带模型，创建后在卡片内添加
        const models: ProviderFormModel[] = []
        await createProvider({
          name: values.name.trim(),
          base_url: values.base_url.trim(),
          api_key: values.api_key?.trim() || null,
          timeout_seconds: values.timeout_seconds,
          enabled: values.enabled,
          models,
        })
        message.success('服务商已创建，请添加可用模型')
      }
      await refreshSetup()
      onClose()
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={isEdit ? '编辑模型服务商' : '添加模型服务商'}
      onCancel={onClose}
      onOk={() => void handleOk()}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
      destroyOnClose
      width={520}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="name"
          label="服务商名称"
          rules={[{ required: true, message: '请输入名称' }]}
        >
          <Input placeholder="例如：OpenAI、DeepSeek、本地 Ollama" />
        </Form.Item>

        <Form.Item
          name="base_url"
          label="Base URL（OpenAI 兼容）"
          rules={[
            { required: true, message: '请输入 Base URL' },
            {
              validator: (_rule, value: string) => {
                if (!value) return Promise.resolve()
                try {
                  const url = new URL(value.trim())
                  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
                    return Promise.reject(new Error('仅支持 http/https'))
                  }
                  return Promise.resolve()
                } catch {
                  return Promise.reject(new Error('URL 格式不正确'))
                }
              },
            },
          ]}
          extra="示例：https://api.openai.com/v1、http://localhost:11434/v1"
        >
          <Input placeholder="https://api.example.com/v1" />
        </Form.Item>

        <Form.Item
          name="api_key"
          label="API Key"
          extra={
            isEdit && provider?.has_api_key
              ? `已保存 ${provider.api_key_masked}，留空表示不修改`
              : '将使用对称加密保存在本机数据库中'
          }
        >
          <Input.Password placeholder={isEdit ? '留空不修改' : 'sk-...'} autoComplete="new-password" />
        </Form.Item>

        <div className="form-row-2col">
          <Form.Item
            name="timeout_seconds"
            label="超时时间（秒）"
            rules={[{ required: true, message: '请输入超时' }]}
          >
            <InputNumber min={5} max={600} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch checkedChildren="开" unCheckedChildren="关" />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  )
}
