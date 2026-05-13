import { useMemo, memo } from 'react'
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

// 使用缓存避免重复渲染相同的公式内容
const formulaCache = new Map<string, string>()
const MAX_CACHE_SIZE = 500

function cachedRender(formula: string, displayMode: boolean): string {
  const cacheKey = `${displayMode ? 'D' : 'I'}:${formula}`
  
  if (formulaCache.has(cacheKey)) {
    return formulaCache.get(cacheKey)!
  }
  
  let result: string
  try {
    result = katex.renderToString(formula, { displayMode, throwOnError: false })
  } catch {
    result = `<span style="color: gray; font-style: italic;">${escapeHtml(formula)}</span>`
  }
  
  // 清理缓存防止内存泄漏
  if (formulaCache.size >= MAX_CACHE_SIZE) {
    const firstKey = formulaCache.keys().next().value
    if (firstKey) {
      formulaCache.delete(firstKey)
    }
  }
  
  formulaCache.set(cacheKey, result)
  return result
}

const MathRenderer = memo(({ content, displayMode = false, maxLength, className }: MathRendererProps) => {
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
        return cachedRender(formula, true)
      })

      // 处理行内公式 $...$
      text = text.replace(/\$([^$]+?)\$/g, (_, formula) => {
        return cachedRender(formula, false)
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
}, (prev, next) => {
  // 自定义比较函数，避免不必要的重渲染
  return prev.content === next.content && 
         prev.displayMode === next.displayMode && 
         prev.maxLength === next.maxLength &&
         prev.className === next.className
})

export default MathRenderer
