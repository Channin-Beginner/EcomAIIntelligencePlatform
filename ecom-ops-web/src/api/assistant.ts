import http, { type CommonResult } from './http'

export interface ChartPayload {
  type: 'line' | 'bar' | 'pie' | 'funnel' | 'table' | 'none'
  title: string
  option?: Record<string, unknown> | null
}

export interface TablePayload {
  columns: string[]
  rows: unknown[][]
}

export interface AssistantQueryResult {
  answer: string
  route: 'template' | 'nl2sql' | 'fallback'
  refDate: string
  sql?: string | null
  chart: ChartPayload
  table?: TablePayload | null
}

export async function fetchAssistantSuggestions() {
  const res = (await http.get('/ops/assistant/suggestions')) as CommonResult<string[]>
  return res.data
}

export async function queryAssistant(question: string, refDate?: string) {
  const res = (await http.post(
    '/ops/assistant/query',
    { question, refDate },
    { timeout: 90000 },
  )) as CommonResult<AssistantQueryResult>
  return res.data
}
