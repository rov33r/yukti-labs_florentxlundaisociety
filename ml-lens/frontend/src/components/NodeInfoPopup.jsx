import React from 'react'
import { X, Info } from 'lucide-react'
import LatexEquation from './LatexEquation'

const KIND_COLORS = {
  input_embedding:      { bg: '#EFF6FF', border: '#3B82F6', text: '#1D4ED8' },
  positional_encoding:  { bg: '#F0FDF4', border: '#22C55E', text: '#15803D' },
  multi_head_attention: { bg: '#FDF4FF', border: '#A855F7', text: '#7E22CE' },
  attention:            { bg: '#FDF4FF', border: '#A855F7', text: '#7E22CE' },
  feedforward:          { bg: '#FFF7ED', border: '#F97316', text: '#C2410C' },
  layernorm:            { bg: '#F0F9FF', border: '#0EA5E9', text: '#0369A1' },
  rmsnorm:              { bg: '#F0F9FF', border: '#0EA5E9', text: '#0369A1' },
  residual:             { bg: '#FAFAFA', border: '#6B7280', text: '#374151' },
  softmax:              { bg: '#FFF1F2', border: '#F43F5E', text: '#BE123C' },
  masking:              { bg: '#FFFBEB', border: '#EAB308', text: '#92400E' },
  linear_projection:    { bg: '#F0FDFA', border: '#14B8A6', text: '#0F766E' },
  output_head:          { bg: '#FEF2F2', border: '#EF4444', text: '#991B1B' },
  other:                { bg: '#F9FAFB', border: '#9CA3AF', text: '#4B5563' },
}

const KIND_GLOSSARY = {
  input_embedding:      'A lookup table that converts each word/token ID into a dense vector of numbers the model can work with.',
  positional_encoding:  'Adds information about where each token sits in the sequence. Without this, the model has no sense of order.',
  multi_head_attention: 'The core mechanism of transformers. Each token looks at every other token and decides how much attention to pay to each one. Running multiple heads in parallel lets the model focus on different types of relationships simultaneously.',
  attention:            'The core mechanism of transformers. Each token looks at every other token and decides how much weight to give each one.',
  feedforward:          'A small two-layer network applied to each token independently after attention. It is where most of the model capacity lives.',
  layernorm:            'Rescales the activations after each sublayer so values stay in a healthy range. Prevents training from becoming unstable.',
  rmsnorm:              'A simpler and faster variant of Layer Normalization that only scales values, without centering them. Often used in modern LLMs.',
  residual:             'A skip connection that adds the input directly to the output. This lets gradients flow back easily during training and prevents information loss.',
  softmax:              'Converts raw attention scores into probabilities that sum to 1. Determines how much each token attends to each other token.',
  masking:              'Blocks certain attention connections. In decoders, this prevents tokens from looking at future tokens they have not seen yet.',
  linear_projection:    'A trainable linear transformation that maps from one vector space to another.',
  output_head:          'The final layer that maps from the model dimension to the vocabulary size, producing a probability distribution over the next token.',
}

export default function NodeInfoPopup({ component, manifest, onClose }) {
  if (!component) return null

  const tc = (manifest?.tensor_contracts ?? []).find((t) => t.component_id === component.id)
  const invs = (manifest?.invariants ?? []).filter((i) =>
    (i.affected_components ?? []).includes(component.id)
  )
  const colors = KIND_COLORS[component.kind] ?? KIND_COLORS.other
  const glossaryEntry = KIND_GLOSSARY[component.kind]

  return (
    <div className="node-popup">
      <div className="node-popup-header">
        <div className="node-popup-title-row">
          <span className="node-popup-title">{component.name}</span>
          <span
            className="node-popup-type-badge"
            style={{
              background: colors.bg,
              color: colors.text,
              border: `1px solid ${colors.border}`,
            }}
          >
            {component.kind.replace(/_/g, ' ')}
          </span>
        </div>
        <button className="node-popup-close" onClick={onClose} aria-label="Close">
          <X size={14} />
        </button>
      </div>

      <div className="node-popup-body">
        <p className="node-popup-summary">{component.description}</p>

        {component.equations?.length > 0 && (
          <div className="node-popup-why">
            <span className="node-popup-why-label">Key equations</span>
            <div className="latex-equation-list">
              {component.equations.map((eq, i) => (
                <LatexEquation key={i} src={eq} block />
              ))}
            </div>
          </div>
        )}

        {Object.keys(component.hyperparameters ?? {}).length > 0 && (
          <div className="node-popup-params">
            <div className="params-header">
              <span className="params-title">Hyperparameters</span>
            </div>
            <div className="params-grid">
              {Object.entries(component.hyperparameters).map(([k, v]) => (
                <React.Fragment key={k}>
                  <label className="param-label" style={{ fontFamily: 'monospace' }}>{k}</label>
                  <span style={{ fontSize: 12, color: '#4B5E78', alignSelf: 'center' }}>{v}</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {tc && (
          <div className="node-popup-why" style={{ marginTop: 12 }}>
            <span className="node-popup-why-label">Tensor shapes</span>
            <div style={{ fontSize: 12, marginTop: 4 }}>
              <div><strong>In:</strong> {Object.entries(tc.input_shapes).map(([k, v]) => `${k}: [${v.join(', ')}]`).join(' / ')}</div>
              <div><strong>Out:</strong> {Object.entries(tc.output_shapes).map(([k, v]) => `${k}: [${v.join(', ')}]`).join(' / ')}</div>
            </div>
          </div>
        )}

        {component.quote?.text && (
          <div className="node-popup-why" style={{ marginTop: 12 }}>
            <span className="node-popup-why-label">Paper quote</span>
            <p style={{ fontStyle: 'italic', fontSize: 12, color: '#4B5E78' }}>"{component.quote.text}"</p>
          </div>
        )}

        {invs.length > 0 && (
          <div className="node-popup-why" style={{ marginTop: 12 }}>
            <span className="node-popup-why-label">Invariants</span>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {invs.map((inv) => (
                <li key={inv.id} style={{ fontSize: 12, marginBottom: 4 }}>{inv.description}</li>
              ))}
            </ul>
          </div>
        )}

        {glossaryEntry && (
          <div className="node-popup-glossary">
            <Info size={12} className="node-popup-glossary-icon" />
            <p className="node-popup-glossary-text">{glossaryEntry}</p>
          </div>
        )}
      </div>
    </div>
  )
}
