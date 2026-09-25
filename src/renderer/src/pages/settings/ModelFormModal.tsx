import { App, Form, Input, Modal, Select, Switch } from 'antd'
import { useEffect, useState } from 'react'
import { useConfigStore } from '../../stores/config-store'
import { useAppStore } from '../../stores/app-store'
import type { ModelConfig, Provider } from '../../types/api'

interface Props {
  open: boolean
  provider: Provider
  model: ModelConfig | null
  onClose: () => void
}

const CAPABILITY_OPTIONS = [
  { label: '对话 chat', value: 'chat' },
  { label: '推理 reasoning', value: 'reasoning' },
  { label: '视觉 vision', value: 'vision' },
  { label: '嵌入 embedding', value: 'embedding' },
]

interface FormValues {
  model_id: string
  display_name: string
  capabilities: string[]
  is_default: boolean
}

export default function ModelFormModal({ open, provider, model, onClose }: Props) {
  const isEdit = Boolean(model)
  const { addModel, updateModel } = useConfigStore()
  const refreshSetup = useAppStore((s) => s.refreshSetup)
  const { message } = App.useApp()
  const [form] = Form.useForm<FormValues>()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        model_id: model?.model_id ?? '',
        display_name: model?.display_name ?? '',
        capabilities: model?.capabilities ?? ['chat'],
        is_default: model?.is_default ?? provider.models.length === 0,
      })
    }
  }, [open, model, provider, form])

  const handleOk = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      if (model) {
        await updateModel(model.id, {
          model_id: values.model_id.trim(),
          display_name: values.display_name.trim(),
          capabilities: values.capabilities,
          is_default: values.is_default,
        })
        message.success('模型已更新')
      } else {
        await addModel(provider.id, {
          model_id: values.model_id.trim(),
          display_name: values.display_name.trim(),
          capabilities: values.capabilities,
          is_default: values.is_default,
        })
        message.success('模型已添加')
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
      title={isEdit ? '编辑模型' : `添加模型 · ${provider.name}`}
      onCancel={onClose}
      onOk={() => void handleOk()}
      confirmLoading={saving}
      okText="保存"
      cancelText="取消"
      destroyOnClose
      width={480}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          name="model_id"
          label="模型 ID"
          rules={[{ required: true, message: '请输入上游模型 ID' }]}
          extra="调用接口时使用的真实名称，如 gpt-4o-mini、deepseek-chat、qwen2.5:7b"
        >
          <Input placeholder="gpt-4o-mini" />
        </Form.Item>
        <Form.Item
          name="display_name"
          label="显示名称"
          rules={[{ required: true, message: '请输入显示名称' }]}
        >
          <Input placeholder="GPT-4o Mini" />
        </Form.Item>
        <Form.Item name="capabilities" label="能力标签">
          <Select mode="tags" options={CAPABILITY_OPTIONS} placeholder="选择或输入能力标签" />
        </Form.Item>
        <Form.Item name="is_default" label="默认模型" valuePropName="checked">
          <Switch checkedChildren="默认" unCheckedChildren="非默认" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
