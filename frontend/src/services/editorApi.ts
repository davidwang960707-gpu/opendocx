/** Editor AI 客户端 — P0-B-4
 *
 * 调 POST /api/v1/editor/ai，解析 SSE 流，暴露 3 个方法：
 * - streamAction(): 通用流式调用（返回 async iterator）
 * - getActions():   获取动作清单
 * - getHealth():    检查 provider 配置
 *
 * 用 fetch + ReadableStream 处理 SSE，避开 axios 不支持流的问题。
 */
import type { ApiResponse } from '../types/api'

export interface AIAction {
  id: string
  label: string
  icon: string
  needs: string[]
}

export interface AIStreamEvent {
  event: 'meta' | 'token' | 'done' | 'error'
  data: any
}

/** P1-UI-6 /api/v1/editor/analyze 响应 */
export interface AnalyzeResponse {
  summary: { text: string; confidence: number }
  health: {
    score: number
    grade: string
    breakdown: { heading: number; code: number; paragraph: number; link: number }
    stats?: {
      lines: number; chars: number; h1: number; h2: number; h3: number
      code_ratio: number; code_langs: string[]; paragraphs: number
      avg_paragraph_length: number; links: number
    }
  }
  terminology: {
    terms: { term: string; count: number }[]
    issues: string[]
  }
  interface: {
    endpoints: { method: string; path: string }[]
    error_codes: number[]
    issues: string[]
  }
  knowledge: {
    related: { id: string; title: string; match_count: number; matched_terms: string[] }[]
  }
}

const BASE = '/api/v1/editor'

function getToken(): string {
  return localStorage.getItem('token') || ''
}

export const editorApi = {
  /** 健康检查 — GET /api/v1/editor/health */
  async getHealth(): Promise<{ ok: boolean; provider?: string; model?: string; error?: string }> {
    const r = await fetch(`${BASE}/health`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    return r.json()
  },

  /** 动作清单 — GET /api/v1/editor/actions */
  async getActions(): Promise<AIAction[]> {
    const r = await fetch(`${BASE}/actions`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) throw new Error(`getActions failed: ${r.status}`)
    const data: ApiResponse<{ actions: AIAction[] }> = await r.json()
    return data.data.actions
  },

  /** P1-UI-6 文档分析 — POST /api/v1/editor/analyze */
  async analyze(content: string, versionId?: string, docId?: string): Promise<AnalyzeResponse> {
    const r = await fetch(`${BASE}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        content,
        version_id: versionId,
        doc_id: docId,
      }),
    })
    if (!r.ok) throw new Error(`editor/analyze ${r.status}: ${await r.text()}`)
    return r.json()
  },

  /**
   * 流式 AI 调用 — POST /api/v1/editor/ai
   * 返回 AsyncGenerator，逐个 yield { event, data }。
   * 调用方拿 SSE 事件做 UI 更新。
   */
  async *streamAction(req: {
    action: string
    content: string
    selection?: string
    question?: string
    context?: Record<string, any>
    temperature?: number
    max_tokens?: number
  }): AsyncGenerator<AIStreamEvent> {
    const r = await fetch(`${BASE}/ai`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(req),
    })

    if (!r.ok) {
      // R12: 503 llm_not_configured 等业务错误, 后端返结构化 detail
      // 试着解析 detail 拿到清晰 message 给用户
      let errMsg = `editor/ai ${r.status}`
      try {
        const body = await r.json()
        if (body?.detail?.message) errMsg = body.detail.message
        else if (typeof body?.detail === 'string') errMsg = body.detail
        else errMsg = errMsg + ': ' + (await r.text().catch(() => ''))
      } catch {
        errMsg = errMsg + ': ' + (await r.text().catch(() => ''))
      }
      throw new Error(errMsg)
    }
    if (!r.body) throw new Error('No response body')

    const reader = r.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE 事件以 \n\n 分隔
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''  // 留下未完成的部分

      for (const part of parts) {
        if (!part.trim()) continue
        const lines = part.split('\n')
        let event: string | null = null
        let data = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) event = line.slice(7).trim()
          else if (line.startsWith('data: ')) data += line.slice(6)
        }
        if (event && data) {
          try {
            yield { event: event as any, data: JSON.parse(data) }
          } catch {
            // 忽略非 JSON 行
          }
        }
      }
    }
  },
}
