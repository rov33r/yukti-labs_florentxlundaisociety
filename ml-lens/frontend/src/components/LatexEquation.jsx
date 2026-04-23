import React, { useRef, useEffect, useState } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'

/**
 * Renders a LaTeX equation string using KaTeX.
 * Block equations auto-scale down via CSS transform if they overflow the card,
 * so no horizontal scrollbar ever appears.
 */
export default function LatexEquation({ src = '', block = false }) {
  if (!src) return null

  // Normalise: strip surrounding $…$ or $$…$$ wrappers the LLM sometimes adds
  let tex = src.trim()
  if (tex.startsWith('$$') && tex.endsWith('$$')) {
    tex = tex.slice(2, -2).trim()
    block = true
  } else if (tex.startsWith('$') && tex.endsWith('$')) {
    tex = tex.slice(1, -1).trim()
  }

  const isBlock =
    block ||
    tex.includes('\n') ||
    tex.includes('\\begin') ||
    tex.includes('\\frac') ||
    tex.includes('\\sum') ||
    tex.includes('\\prod') ||
    tex.includes('\\int')

  const fallback = <span className="latex-fallback">{src}</span>

  if (!isBlock) {
    try {
      return (
        <span className="latex-inline">
          <InlineMath math={tex} renderError={() => fallback} />
        </span>
      )
    } catch {
      return fallback
    }
  }

  return <ScaledBlockMath tex={tex} fallback={fallback} />
}

/** Renders a block equation and scales it down to fit its container. */
function ScaledBlockMath({ tex, fallback }) {
  const outerRef = useRef(null)
  const innerRef = useRef(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const measure = () => {
      const outer = outerRef.current
      const inner = innerRef.current
      if (!outer || !inner) return
      const outerW = outer.clientWidth
      const innerW = inner.scrollWidth
      if (innerW > outerW) {
        setScale(outerW / innerW)
      } else {
        setScale(1)
      }
    }

    measure()
    // Re-measure on window resize (e.g. if the popup resizes)
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [tex])

  try {
    return (
      <div className="latex-block" ref={outerRef}>
        <div
          ref={innerRef}
          style={{
            transformOrigin: 'center top',
            transform: scale < 1 ? `scale(${scale})` : 'none',
            // Prevent the scaled-down element from still taking up original space
            marginBottom: scale < 1 ? `${-(innerRef.current?.scrollHeight ?? 0) * (1 - scale)}px` : 0,
          }}
        >
          <BlockMath math={tex} renderError={() => fallback} />
        </div>
      </div>
    )
  } catch {
    return fallback
  }
}
