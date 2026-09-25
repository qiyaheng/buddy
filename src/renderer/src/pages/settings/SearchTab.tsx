import { App, Button, Form, Input, Radio } from 'antd'
import { useEffect, useState } from 'react'
import { useConfigStore } from '../../stores/config-store'

export default function SearchTab() {
  const { settings, saveSettings, resetTavilyKey } = useConfigStore()
  const { message } = App.useApp()
  const [form] = Form.useForm<{ search_provider: 'duckduckgo' | 'tavily'; tavily_api_key: string }>()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (settings) {
      form.setFieldsValue({ search_provider: settings.search_provider, tavily_api_key: '' })
    }
  }, [settings, form])

  const provider = Form.useWatch('search_provider', form) as 'duckduckgo' | 'tavily' | undefined

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await saveSettings({
        search_provider: values.search_provider,
        tavily_api_key: values.tavily_api_key?.trim() || undefined,
      })
      message.success('搜索设置已保存')
      form.setFieldValue('tavily_api_key', '')
    } catch (err) {
      message.error(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-pane settings-pane-narrow">
      <p className="settings-section-desc">配置深度调研使用的联网搜索引擎。</p>

      <Form form={form} layout="vertical">
        <Form.Item
          name="search_provider"
          label="搜索引擎"
          rules={[{ required: true, message: '请选择搜索引擎' }]}
        >
          <Radio.Group className="search-radio-group">
            <Radio value="duckduckgo" className="search-radio-card">
              <div className="search-option-title">
                DuckDuckGo
                <span className="search-option-badge">免配置 · 推荐</span>
              </div>
              <div className="search-option-desc">无需 API Key，开箱即用，适合大多数调研场景</div>
            </Radio>
            <Radio value="tavily" className="search-radio-card">
              <div className="search-option-title">Tavily</div>
              <div className="search-option-desc">面向 AI 优化的搜索 API，结果质量更高，需要 API Key</div>
            </Radio>
          </Radio.Group>
        </Form.Item>

        {provider === 'tavily' && (
          <Form.Item
            name="tavily_api_key"
            label="Tavily API Key"
            extra={
              settings?.has_tavily_key ? (
                <span>
                  已保存 <code className="settings-mono">{settings.tavily_api_key_masked}</code>
                  ，留空表示不修改；也可以
                  <Button
                    type="link"
                    size="small"
                    style={{ padding: '0 4px' }}
                    onClick={async () => {
                      await resetTavilyKey()
                      message.success('已清除 Tavily Key')
                    }}
                  >
                    清除已保存的 Key
                  </Button>
                </span>
              ) : (
                '在 tavily.com 注册获取，Key 将加密保存在本机'
              )
            }
          >
            <Input.Password placeholder="tvly-..." autoComplete="new-password" />
          </Form.Item>
        )}

        <Button type="primary" loading={saving} onClick={() => void handleSave()}>
          保存
        </Button>
      </Form>
    </div>
  )
}
