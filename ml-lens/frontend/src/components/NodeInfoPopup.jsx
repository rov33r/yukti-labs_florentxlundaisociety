import React from 'react'
import LatexEquation from './LatexEquation'

export default function NodeInfoPopup({ component, manifest, onClose }) {
  if (!component) return null

  const tc = (manifest?.tensor_contracts ?? []).find((t) => t.component_id === component.id)
  const invs = (manifest?.invariants ?? []).filter((i) =>
    (i.affected_components ?? []).includes(component.id)
  )

  return (
    <div className="node-popup">
      <div className="node-popup-header">
        <div className="node-popup-title-row">
          <span className="node-popup-title">{component.name}</span>
          <span
            className="node-popup-type-badge"
            style={{ background: '#EDF7ED', color: '#16A34A', border: '1px solid #16A34A' }}
          >
            {component.kind.replace(/_/g, ' ')}
          </span>
        </div>
        <button className="node-popup-close" onClick={onClose} aria-label="Close">✕</button>
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
              <div><strong>In:</strong> {Object.entries(tc.input_shapes).map(([k, v]) => `${k}: [${v.join(', ')}]`).join(' · ')}</div>
              <div><strong>Out:</strong> {Object.entries(tc.output_shapes).map(([k, v]) => `${k}: [${v.join(', ')}]`).join(' · ')}</div>
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
      </div>
    </div>
  )
}
