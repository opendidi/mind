/** Parse agent message text into typed segments (mindmap, map, route, files, code, text). */

const BLOCK_RE = /```(\w*)\s*\n?([\s\S]*?)```/g

export type BlockType = 'mindmap' | 'map' | 'route' | 'files'

export interface MsgSegment {
  type: 'text' | BlockType | 'code'
  content?: string
  data?: unknown
  language?: string
}

export function parseMessageSegments(text: string): MsgSegment[] {
  BLOCK_RE.lastIndex = 0
  const segments: MsgSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = BLOCK_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) })
    }
    const blockType = match[1]
    const blockContent = match[2].trim()
    if (blockType === 'mindmap') {
      segments.push({ type: 'mindmap', content: blockContent })
    } else if (blockType === 'map' || blockType === 'route' || blockType === 'files') {
      try {
        const data = JSON.parse(blockContent)
        segments.push({ type: blockType, data })
      } catch {
        segments.push({ type: 'code', language: blockType, content: blockContent })
      }
    } else {
      segments.push({ type: 'code', language: blockType, content: blockContent })
    }
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }
  return segments.length > 0 ? segments : [{ type: 'text', content: text }]
}
