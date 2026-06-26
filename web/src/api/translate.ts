import http from '@/utils/request'

export interface TranslateRequest {
  text: string
  target_lang?: string
  source_lang?: string
  style?: string
}

export interface TranslateResult {
  translated: string
  engine: string
  source_lang: string
  target_lang: string
}

export async function translateText(data: TranslateRequest): Promise<TranslateResult> {
  const res = await http.post('/translate/translate', data)
  if (res.code === 200) {
    return res.data as TranslateResult
  }
  throw new Error(res.message || '翻译失败')
}

export async function getTranslateLanguages() {
  const res = await http.get('/translate/languages')
  return res.data
}
