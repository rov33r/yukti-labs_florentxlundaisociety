import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const components = {
  h1: ({ children }) => <h1 className="md-h1">{children}</h1>,
  h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
  h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
  p:  ({ children }) => <p  className="md-p">{children}</p>,
  strong: ({ children }) => <strong className="md-strong">{children}</strong>,
  em:     ({ children }) => <em className="md-em">{children}</em>,
  ul: ({ children }) => <ul className="md-ul">{children}</ul>,
  ol: ({ children }) => <ol className="md-ol">{children}</ol>,
  li: ({ children }) => <li className="md-li">{children}</li>,
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
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
