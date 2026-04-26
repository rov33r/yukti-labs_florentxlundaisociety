import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { GLOSSARY } from '../content/glossary'

const SORTED_TERMS = Object.keys(GLOSSARY)
  .filter(t => t.length >= 5)
  .sort((a, b) => b.length - a.length)

function annotateText(text) {
  if (!text || typeof text !== 'string') return text

  const parts = []
  let remaining = text
  let keyIdx = 0

  while (remaining.length > 0) {
    let earliest = -1
    let matchedTerm = null

    for (const term of SORTED_TERMS) {
      const idx = remaining.toLowerCase().indexOf(term.toLowerCase())
      if (idx === -1) continue

      const before = remaining[idx - 1]
      const after = remaining[idx + term.length]
      const wordBefore = !before || /\W/.test(before)
      const wordAfter = !after || /\W/.test(after)
      if (!wordBefore || !wordAfter) continue

      if (earliest === -1 || idx < earliest) {
        earliest = idx
        matchedTerm = term
      }
    }

    if (!matchedTerm) {
      parts.push(remaining)
      break
    }

    if (earliest > 0) parts.push(remaining.slice(0, earliest))

    const matchedText = remaining.slice(earliest, earliest + matchedTerm.length)
    parts.push(
      <abbr key={keyIdx++} title={GLOSSARY[matchedTerm.toLowerCase()]} className="glossary-term">
        {matchedText}
      </abbr>
    )
    remaining = remaining.slice(earliest + matchedTerm.length)
  }

  return parts
}

function processNode(child) {
  if (typeof child === 'string') return annotateText(child)
  if (React.isValidElement(child) && child.props.children) {
    return React.cloneElement(child, {}, processNode(child.props.children))
  }
  if (Array.isArray(child)) return child.map(processNode)
  return child
}

const components = {
  h1: ({ children }) => <h1 className="md-h1">{children}</h1>,
  h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
  h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
  p:  ({ children }) => <p className="md-p">{processNode(children)}</p>,
  strong: ({ children }) => <strong className="md-strong">{children}</strong>,
  em:     ({ children }) => <em className="md-em">{children}</em>,
  ul: ({ children }) => <ul className="md-ul">{children}</ul>,
  ol: ({ children }) => <ol className="md-ol">{children}</ol>,
  li: ({ children }) => <li className="md-li">{processNode(children)}</li>,
  blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
  code: ({ inline, children }) =>
    inline
      ? <code className="md-code-inline">{children}</code>
      : <pre className="md-pre"><code>{children}</code></pre>,
  hr: () => <hr className="md-hr" />,
  a:  ({ href, children }) => (
    <a className="md-link" href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

export default function MarkdownMessage({ content }) {
  return (
    <div className="md-root">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
