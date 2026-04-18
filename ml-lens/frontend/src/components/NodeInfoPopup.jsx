import React, { useState, useEffect } from 'react'
import { PARAM_META, PARAM_DEFAULTS, isModified, getValidationWarnings } from '../hyperparameters'

const NODE_INFO = {
  '1': {
    title: 'Input Tokens',
    type: 'Input',
    summary: 'Raw text is split into subword units called tokens. Each token is assigned an integer ID from a fixed vocabulary (e.g. 50,000 entries). This is the only place text enters the model — everything downstream operates on these IDs.',
    why: 'Tokenisation lets the model handle any word, including rare ones, by breaking them into known pieces. "unhappiness" might become ["un", "happi", "ness"].',
  },
  '2': {
    title: 'Input Embedding',
    type: 'Encoder',
    summary: 'Each token ID is looked up in a learned embedding table and converted into a dense vector (e.g. 512 dimensions). Similar tokens end up close together in this vector space.',
    why: 'Integers have no geometric meaning — "cat" (ID 482) isn\'t numerically related to "kitten" (ID 9103). Embeddings give the model a continuous space where similarity can be computed.',
  },
  '3': {
    title: 'Positional Encoding',
    type: 'Encoder',
    summary: 'Sine and cosine waves of different frequencies are added to each embedding to encode its position in the sequence. Position 0 gets one pattern, position 1 another, and so on.',
    why: 'Attention treats all tokens equally regardless of order. Without positional encoding, "dog bites man" and "man bites dog" would look identical to the model.',
  },
  '4': {
    title: 'Encoder (×6)',
    type: 'Encoder',
    summary: 'Six identical layers stacked sequentially. Each layer contains a Multi-Head Attention sub-layer followed by a Feed Forward sub-layer, with residual connections and layer norm around each.',
    why: 'Depth lets the model build increasingly abstract representations. Early layers capture syntax; later layers capture semantics and long-range relationships.',
  },
  '5': {
    title: 'Multi-Head Attention',
    type: 'Sub-layer',
    summary: 'Each token computes a query, and attends to all other tokens\' keys, producing a weighted sum of their values. Running H heads in parallel lets the model focus on different relationship types simultaneously.',
    why: 'A single attention head can only capture one "view" of the sequence. Multiple heads allow the model to simultaneously track grammatical agreement, coreference, and semantic roles.',
  },
  '6': {
    title: 'Feed Forward',
    type: 'Sub-layer',
    summary: 'A two-layer MLP (expand → activation → project) applied independently to each token position. The hidden dimension is typically 4× the model dimension (e.g. 2048 for a 512-dim model).',
    why: 'Attention mixes information across positions; the FFN processes each position\'s representation in isolation, adding capacity without cross-position interaction.',
  },
  '7': {
    title: 'Decoder (×6)',
    type: 'Decoder',
    summary: 'Six layers that generate the output sequence one token at a time. Each layer has three sub-layers: Masked Self-Attention, Cross-Attention over the encoder output, and Feed Forward.',
    why: 'The decoder must be able to see the encoder\'s full context (via cross-attention) while only attending to tokens it has already generated (via masking), preventing it from "cheating" at training time.',
  },
  '8': {
    title: 'Masked Attention',
    type: 'Decoder',
    summary: 'Self-attention within the decoder, but with a causal mask that sets future positions to −∞ before softmax. This means each output token can only attend to itself and earlier tokens.',
    why: 'During training the full target sequence is fed in at once for efficiency. The mask enforces autoregressive behaviour — the model cannot see the answer it\'s supposed to predict.',
  },
  '9': {
    title: 'Cross Attention',
    type: 'Decoder',
    summary: 'Queries come from the decoder\'s current state; keys and values come from the encoder\'s final output. This is the bridge that lets the decoder "read" the encoded input at every generation step.',
    why: 'Without this, the decoder would have no access to the source sequence — cross-attention is how the model knows what to translate or summarise.',
  },
  '10': {
    title: 'Linear + Softmax',
    type: 'Output',
    summary: 'A linear projection maps the decoder\'s hidden state to vocabulary size (e.g. 50,000 logits). Softmax converts those logits into a probability distribution, and the highest-probability token is selected.',
    why: 'The model\'s internal representation needs to be mapped back to a discrete token choice. Temperature can be applied to the logits here to control how "sharp" or "random" the sampling is.',
  },
}

const TYPE_BADGE = {
  Input:       { bg: '#EEF3FA', color: '#1E3A5F', border: '#D6E4F0' },
  Encoder:     { bg: '#EEF3FA', color: '#1E3A5F', border: '#1E3A5F' },
  Decoder:     { bg: '#FFF7ED', color: '#C2410C', border: '#F97316' },
  'Sub-layer': { bg: '#F5F5F5', color: '#4B5E78', border: '#D6E4F0' },
  Output:      { bg: '#EEF3FA', color: '#1E3A5F', border: '#1E3A5F' },
}

function formatDisplay(num, type) {
  if (type === 'float') return num.toString()
  return Number.isFinite(num) ? num.toLocaleString('en-US') : ''
}

function parseRaw(str, type) {
  const cleaned = str.replace(/,/g, '').trim()
  return type === 'float' ? parseFloat(cleaned) : parseInt(cleaned, 10)
}

function ParamField({ meta, value, defaultValue, onChange }) {
  const changed = value !== defaultValue
  const [display, setDisplay] = useState(() => formatDisplay(value, meta.type))
  const [focused, setFocused] = useState(false)

  // Sync display when value changes externally (e.g. Reset)
  useEffect(() => {
    if (!focused) setDisplay(formatDisplay(value, meta.type))
  }, [value, focused])

  if (meta.type === 'select') {
    return (
      <div className="param-field-wrap">
        <select
          className={`param-select ${changed ? 'param-changed' : ''}`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          {meta.options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
        {changed && (
          <span className="param-default-hint">default: {defaultValue}</span>
        )}
      </div>
    )
  }

  const handleFocus = (e) => {
    setFocused(true)
    // Show raw number while editing so typing is uninterrupted
    setDisplay(value.toString())
    e.target.select()
  }

  const handleChange = (e) => {
    // Allow digits, commas, and decimal points while typing
    const raw = e.target.value.replace(/[^0-9.,]/g, '')
    setDisplay(raw)
  }

  const handleBlur = () => {
    setFocused(false)
    const num = parseRaw(display, meta.type)
    if (Number.isFinite(num)) {
      const lo = meta.min ?? -Infinity
      const hi = meta.max ?? Infinity
      const clamped = Math.min(hi, Math.max(lo, num))
      onChange(clamped)
      setDisplay(formatDisplay(clamped, meta.type))
    } else {
      setDisplay(formatDisplay(value, meta.type))
    }
  }

  const step = (dir) => {
    const lo = meta.min ?? -Infinity
    const hi = meta.max ?? Infinity
    const next = Math.min(hi, Math.max(lo, value + dir * meta.step))
    onChange(next)
  }

  return (
    <div className="param-field-wrap">
      <div className="param-input-group">
        <input
          className={`param-input ${changed ? 'param-changed' : ''}`}
          type="text"
          inputMode={meta.type === 'float' ? 'decimal' : 'numeric'}
          value={display}
          onFocus={handleFocus}
          onChange={handleChange}
          onBlur={handleBlur}
        />
        <div className="param-steppers">
          <button className="param-step-btn" onMouseDown={(e) => { e.preventDefault(); step(1) }}>▲</button>
          <button className="param-step-btn" onMouseDown={(e) => { e.preventDefault(); step(-1) }}>▼</button>
        </div>
        {meta.unit && <span className="param-unit">{meta.unit}</span>}
      </div>
      {changed && (
        <span className="param-default-hint">
          default: {formatDisplay(defaultValue, meta.type)}
        </span>
      )}
    </div>
  )
}

export default function NodeInfoPopup({ node, params, onParamChange, onParamReset, onClose }) {
  if (!node) return null

  const info = NODE_INFO[node.id]
  const paramMeta = PARAM_META[node.id] || []
  if (!info) return null

  const badge = TYPE_BADGE[info.type] || TYPE_BADGE['Sub-layer']
  const modified = isModified(node.id, params)
  const warnings = getValidationWarnings(node.id, params)

  return (
    <div className="node-popup">
      <div className="node-popup-header">
        <div className="node-popup-title-row">
          <span className="node-popup-title">{info.title}</span>
          <span
            className="node-popup-type-badge"
            style={{ background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}
          >
            {info.type}
          </span>
        </div>
        <button className="node-popup-close" onClick={onClose} aria-label="Close">✕</button>
      </div>

      <div className="node-popup-body">
        <p className="node-popup-summary">{info.summary}</p>

        <div className="node-popup-why">
          <span className="node-popup-why-label">Why it matters</span>
          <p>{info.why}</p>
        </div>

        {paramMeta.length > 0 && (
          <div className="node-popup-params">
            <div className="params-header">
              <span className="params-title">Parameters</span>
              {modified && (
                <button
                  className="params-reset-btn"
                  onClick={() => onParamReset(node.id)}
                >
                  Reset
                </button>
              )}
            </div>

            <div className="params-grid">
              {paramMeta.map((meta) => {
                const defaultValue = PARAM_DEFAULTS[node.id][meta.key]
                const currentValue = params?.[meta.key] ?? defaultValue
                return (
                  <React.Fragment key={meta.key}>
                    <label className={`param-label ${currentValue !== defaultValue ? 'param-label-changed' : ''}`}>
                      {meta.label}
                    </label>
                    <ParamField
                      meta={meta}
                      value={currentValue}
                      defaultValue={defaultValue}
                      onChange={(val) => onParamChange(node.id, meta.key, val)}
                    />
                  </React.Fragment>
                )
              })}
            </div>

            {warnings.length > 0 && (
              <div className="params-warnings">
                {warnings.map((w, i) => (
                  <p key={i} className="param-warning">⚠ {w}</p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
