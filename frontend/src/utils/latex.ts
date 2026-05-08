/** LaTeX 预处理工具 */

/**
 * 清理 LaTeX 内容，移除多余空白
 */
export function cleanLatex(content: string): string {
  return content
    .replace(/\s+/g, ' ')
    .replace(/\$\s+/g, '$')
    .replace(/\s+\$/g, '$')
    .trim();
}

/**
 * 提取纯文本（移除 LaTeX 命令）
 */
export function latexToPlainText(content: string): string {
  return content
    .replace(/\$[^$]*\$/g, '[公式]')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[{}]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * 检查内容是否包含 LaTeX
 */
export function hasLatex(content: string): boolean {
  return /\$[^$]+\$/.test(content) || /\\[a-zA-Z]+/.test(content);
}
