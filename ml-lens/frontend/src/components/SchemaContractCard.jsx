import React from 'react'

export default function SchemaContractCard({ component, contracts = [] }) {
  const contract = contracts.find(c => c.component_id === component.id)

  return (
    <div className="schema-card">
      <div className="schema-card-header">
        <span className="schema-kind-badge">{component.kind}</span>
        <h4 className="schema-card-title">{component.name}</h4>
      </div>

      <p className="schema-card-desc">{component.description}</p>

      {component.equations.length > 0 && (
        <div className="schema-equations">
          {component.equations.map((eq, i) => (
            <code key={i} className="equation">{eq}</code>
          ))}
        </div>
      )}

      {contract && (
        <div className="tensor-contract">
          <span className="contract-label">Tensor Contract</span>
          <div className="shapes-row">
            <div className="shapes-group">
              <span className="shapes-dir">in</span>
              {Object.entries(contract.input_shapes).map(([k, dims]) => (
                <code key={k} className="shape-tag">{k}: [{dims.join(', ')}]</code>
              ))}
            </div>
            <span className="shapes-arrow">→</span>
            <div className="shapes-group">
              <span className="shapes-dir">out</span>
              {Object.entries(contract.output_shapes).map(([k, dims]) => (
                <code key={k} className="shape-tag">{k}: [{dims.join(', ')}]</code>
              ))}
            </div>
          </div>
          {contract.dtype && <span className="dtype-tag">{contract.dtype}</span>}
        </div>
      )}

      {component.depends_on.length > 0 && (
        <div className="depends-row">
          <span className="depends-label">depends on:</span>
          {component.depends_on.map(dep => (
            <code key={dep} className="dep-tag">{dep}</code>
          ))}
        </div>
      )}

      {component.quote && (
        <blockquote className="paper-quote">"{component.quote.text}"
          {component.quote.section && <cite> — {component.quote.section}</cite>}
        </blockquote>
      )}
    </div>
  )
}
