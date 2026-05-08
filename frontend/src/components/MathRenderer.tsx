import { useMemo } from 'react'
import katex from 'katex'

interface MathRendererProps {
  content: string
  displayMode?: boolean
  maxLength?: number
  className?: string
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function MathRenderer({ content, displayMode = false, maxLength, className }: MathRendererProps) {
  const rendered = useMemo(() => {
    if (!content) return ''

    let text = content

    // 截断处理
    if (maxLength && text.length > maxLength) {
      text = text.slice(0, maxLength) + '...'
    }

    try {
      // 处理行间公式 $$...$$
      text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, formula) => {
        try {
          return katex.renderToString(formula, { displayMode: true, throwOnError: false })
        } catch {
          return `<span style="color: gray; font-style: italic;">${escapeHtml(formula)}</span>`
        }
      })

      // 处理行内公式 $...$
      text = text.replace(/\$([^$]+?)\$/g, (_, formula) => {
        try {
          return katex.renderToString(formula, { displayMode: false, throwOnError: false })
        } catch {
          return `<span style="color: gray; font-style: italic;">${escapeHtml(formula)}</span>`
        }
      })

      return text
    } catch {
      return escapeHtml(content)
    }
  }, [content, maxLength])

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: rendered }}
    />
  )
}

export default MathRenderer
