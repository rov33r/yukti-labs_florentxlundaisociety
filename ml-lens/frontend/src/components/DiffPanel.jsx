import React from 'react'

export default function DiffPanel({ schemaDiff }) {
  if (!schemaDiff) return null

  const d_k_old = schemaDiff.base_params.d_model / schemaDiff.base_params.num_heads
  const d_k_new = schemaDiff.modified_params.d_model / schemaDiff.modified_params.num_heads

  const handleDownload = () => {
    const json = JSON.stringify(schemaDiff, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schema_diff.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopyNotes = () => {
    navigator.clipboard.writeText(schemaDiff.implementation_notes)
    alert('Copied to clipboard!')
  }

  return (
    <div style={{ marginTop: '24px', borderTop: '1px solid #E5E5E5', paddingTop: '24px' }}>
      <h3>Schema Diff Results</h3>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <div style={{ background: '#F5F5F5', padding: '12px', borderRadius: '6px' }}>
          num_heads: {schemaDiff.base_params.num_heads} → {schemaDiff.modified_params.num_heads}
        </div>
        <div style={{ background: '#F5F5F5', padding: '12px', borderRadius: '6px' }}>
          d_k: {Math.round(d_k_old)} → {Math.round(d_k_new)}
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h4 style={{ marginBottom: '12px' }}>Component Changes</h4>
        {schemaDiff.component_diffs.map((comp, idx) => (
          <div
            key={idx}
            style={{
              borderLeft: comp.changed ? '3px solid #854F0B' : '3px solid #10B981',
              paddingLeft: '12px',
              marginBottom: '12px',
              paddingTop: '8px',
              paddingBottom: '8px'
            }}
          >
            <div style={{ fontWeight: 600 }}>
              {comp.component_id} {comp.changed && <span style={{ color: '#DC2626' }}>(changed)</span>}
            </div>
            {comp.changed && (
              <>
                <div style={{ fontSize: '0.9em', color: '#666', marginTop: '4px' }}>
                  {comp.old_shapes.input} → {comp.new_shapes.input}
                </div>
                <div style={{ fontSize: '0.9em', marginTop: '6px', color: '#333' }}>
                  {comp.rationale}
                </div>
              </>
            )}
            {comp.invariants_broken.length > 0 && (
              <div style={{ color: '#DC2626', marginTop: '6px', fontSize: '0.9em' }}>
                Broken: {comp.invariants_broken.join(', ')}
              </div>
            )}
            {comp.invariants_broken.length === 0 && comp.changed && (
              <div style={{ color: '#10B981', marginTop: '6px', fontSize: '0.9em' }}>
                ✓ No invariants broken
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ background: '#F9F9F9', padding: '16px', borderRadius: '6px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ margin: 0 }}>Implementation Notes</h4>
          <button onClick={handleCopyNotes} style={{ padding: '6px 12px', fontSize: '0.9em' }}>
            Copy for Claude Code
          </button>
        </div>
        <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto', fontSize: '0.85em', whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {schemaDiff.implementation_notes}
        </pre>
      </div>

      <button onClick={handleDownload} className="btn-primary">
        Download schema_diff.json
      </button>
    </div>
  )
}
