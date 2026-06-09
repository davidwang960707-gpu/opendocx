import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import enUS from 'antd/locale/en_US'
import App from './App'
import { useThemeStore } from './stores/theme'
import { LocaleProvider, useLocale, type Locale } from './i18n'
import './styles/tokens.css'  // Atlas EIDS 9 色 + 玻璃 + 8 档间距 (S1 注入)
import './styles/global.css'
import './styles/app-sider.css'
import './styles/ai-panel.css'
import './styles/ai-floating.css'
import './styles/status-bar.css'
import './styles/command-palette.css'
import './styles/published.css'
import './styles/projects.css'
import './styles/dashboard.css'
import './styles/admin.css'

// Build marker — 确认浏览器加载的是最新 bundle (Vite --force 重新 hash)
console.info('[OpenDocX] main.tsx loaded — build 2026-06-02-fresh')

function Root() {
  // 订阅 theme store 切换 — 切 dark/light 时 AntD 跟着重渲染
  const effective = useThemeStore(s => s.effective)
  const { locale } = useLocale()
  const isDark = effective === 'dark'
  const antdLocale = locale === 'en-US' ? enUS : zhCN
  return (
    <ConfigProvider
      locale={antdLocale}
      theme={{
        // Atlas EIDS 9 色 seed: 主色用 violet (#7B61FF), 暗色下亮一档 (#9B85FF)
        // 圆角 12 (Atlas 推荐, 中卡) + 字体栈 (Inter + HarmonyOS Sans SC)
        token: {
          colorPrimary: isDark ? '#9B85FF' : '#7B61FF',
          colorSuccess: '#10B981',
          colorWarning: '#F97316',
          colorError: '#EF4444',
          colorInfo: '#06B6D4',
          borderRadius: 12,            // Atlas 4 档之一 (sm 8 / md 12 / lg 16 / xl 20)
          borderRadiusLG: 16,
          borderRadiusSM: 8,
          fontFamily: '"Inter", "HarmonyOS Sans SC", -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          fontSize: 14,                // B 紧凑风 14px
          // Atlas 玻璃感: Antd 5 不直接支持 backdrop-filter, 用 token 模拟
          // 实际玻璃靠 global.css .glass 类 + backdrop-filter
          wireframe: false,            // 关掉线框风格, 用填充色块 (更 Atlas 化)
        },
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        // 组件级 token 覆盖 (R 后修订: 间距 16-32 大档 + Form/Table/Space 呼吸感)
        components: {
          Layout: {
            // 浅色主题统一纯浅色; 暗色继续紫调
            headerBg: isDark ? 'rgba(22, 22, 31, 0.78)' : 'rgba(255, 255, 255, 0.78)',
            siderBg: isDark ? '#1e1e2f' : '#F8F9FC',
            bodyBg: isDark ? '#0A0A0B' : '#F7F8FB',
            headerHeight: 48,
            headerPadding: '0 24px',
          },
          Menu: {
            // 悬浮胶囊 — 圆角 10px, 高度 40, 横向 margin 10 (脱离边缘)
            itemBorderRadius: 10,
            itemHeight: 40,
            itemMarginInline: 10,
            itemMarginBlock: 4,
            subMenuItemBorderRadius: 8,
            fontSize: 14,
            iconSize: 16,
            iconMarginInlineEnd: 10,
            // R 后: 浅色走更淡的紫底 (8%), 暗色走原紫 (18%)
            itemSelectedBg: isDark ? 'rgba(155, 133, 255, 0.18)' : 'rgba(123, 97, 255, 0.08)',
            itemSelectedColor: isDark ? '#FFFFFF' : '#1D1D1F',
            itemHoverBg: isDark ? 'rgba(255, 255, 255, 0.04)' : 'rgba(0, 0, 0, 0.04)',
            itemColor: isDark ? '#AEAEB2' : '#6E6E73',
            darkItemBg: 'transparent',
            darkSubMenuItemBg: 'transparent',
          },
          Card: {
            borderRadiusLG: 16,
            paddingLG: 24,                /* R 后: 20→24, 留呼吸 */
          },
          Button: {
            borderRadius: 10,
            controlHeight: 36,
            controlHeightLG: 40,
            controlHeightSM: 28,
            fontWeight: 500,
            primaryShadow: '0 2px 8px rgba(123, 97, 255, 0.28)',
            defaultShadow: 'none',
            paddingInline: 16,            /* R 后: 默认 12→16, 呼吸感 */
            paddingInlineLG: 20,
          },
          Tag: {
            borderRadiusSM: 6,
          },
          Switch: {
            colorPrimary: isDark ? '#9B85FF' : '#7B61FF',
            colorPrimaryHover: isDark ? '#B4A4FF' : '#9B85FF',
            handleSize: 18,               /* R 后: 默认 16→18, 视觉重量 */
          },
          Tabs: {
            titleFontSize: 14,
            horizontalItemPadding: '12px 0',  /* R 后: 10→12 */
            horizontalItemGutter: 32,
            itemSelectedColor: isDark ? '#9B85FF' : '#7B61FF',
            itemHoverColor: isDark ? '#B4A4FF' : '#9B85FF',
            inkBarColor: isDark ? '#9B85FF' : '#7B61FF',
          },
          Drawer: {
            colorBgElevated: isDark ? '#1C1C1E' : '#FFFFFF',
            paddingLG: 24,                /* R 后: drawer 内边距 */
          },
          /* R 后: Form 呼吸感 — label/input 拉开 + 垂直间距 20 */
          Form: {
            itemMarginBottom: 20,
            labelFontSize: 13,
            verticalLabelPadding: '0 0 6px',
          },
          /* R 后: Table 头跟行拉开, cell padding 16 */
          Table: {
            headerBg: isDark ? 'rgba(255, 255, 255, 0.04)' : 'var(--bg-secondary)',
            headerColor: isDark ? '#AEAEB2' : '#6E6E73',
            headerSplitColor: 'transparent',  /* 关掉默认头部分割线, 用 padding 呼吸 */
            cellPaddingBlock: 14,         /* R 后: 11→14, 头/行高 */
            cellPaddingInline: 16,        /* R 后: 12→16, 列宽 */
            cellFontSize: 14,
            headerBorderRadius: 10,       /* 头部行圆角 */
            rowHoverBg: isDark ? 'rgba(255, 255, 255, 0.02)' : 'rgba(123, 97, 255, 0.04)',
          },
          /* R 后: Input 留呼吸, 高度 36, padding 12 */
          Input: {
            controlHeight: 36,
            paddingBlock: 8,
            paddingInline: 12,
          },
          Select: {
            controlHeight: 36,
          },
          /* R 后: Space 默认 size 16 */
          Space: {
            size: 16,
          },
          /* R 后: Modal 标题加粗 + padding 24 */
          Modal: {
            titleFontSize: 16,
            paddingContentHorizontalLG: 24,
          },
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LocaleProvider>
      <Root />
    </LocaleProvider>
  </React.StrictMode>,
)
