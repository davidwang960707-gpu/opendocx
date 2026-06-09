/** LocaleSwitcher — 顶部右上角中英切换按钮
 *
 * 走 useLocale hook 拿 setLocale, 切 zh-CN/en-US 后
 * Antd <ConfigProvider locale> 跟静态站 <html lang> 同步更新
 */

import { Button, Tooltip, Space } from 'antd'
import { GlobalOutlined } from '@ant-design/icons'
import { useLocale, type Locale } from './index'

const LOCALES: Array<{ code: Locale; label: string; short: string }> = [
  { code: 'zh-CN', label: '中文', short: '中' },
  { code: 'en-US', label: 'English', short: 'EN' },
]

export default function LocaleSwitcher() {
  const { locale, setLocale } = useLocale()
  const current = LOCALES.find((l) => l.code === locale) || LOCALES[0]
  const next = LOCALES.find((l) => l.code !== locale) || LOCALES[1]

  return (
    <Tooltip title={`切换到 ${next.label}`}>
      <Button
        type="text"
        size="small"
        icon={<GlobalOutlined />}
        onClick={() => setLocale(next.code)}
        data-testid="locale-switcher"
        style={{ fontSize: 12 }}
      >
        <Space size={4}>
          <span style={{ fontWeight: locale === 'zh-CN' ? 600 : 400 }}>中</span>
          <span style={{ color: 'var(--text-tertiary)' }}>|</span>
          <span style={{ fontWeight: locale === 'en-US' ? 600 : 400 }}>EN</span>
        </Space>
      </Button>
    </Tooltip>
  )
}
