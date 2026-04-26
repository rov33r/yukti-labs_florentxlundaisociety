import React, { useState } from 'react'
import ArchitectureFlow from './ArchitectureFlow'
import NodeInfoPopup from './NodeInfoPopup'
import CodeSandbox from './CodeSandbox'
import TraceView from './TraceView'

function EmptyState() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '100%', color: '#9CA3AF', padding: 32,
    }}>
      <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>㗊</div>
      <p style={{ fontSize: 15, fontWeight: 600, color: '#6B7280', marginBottom: 6 }}>No paper loaded</p>
      <p style={{ fontSize: 13, textAlign: 'center', maxWidth: 280 }}>
        Ingest a paper from the home page to visualize its architecture
      </p>
    </div>
  )
}

export default function Sandbox({ manifest, viewMode }) {
  const [selectedCompId, setSelectedCompId] = useState(null)
  const selectedComponent = manifest?.components?.find(c => c.id === selectedCompId) ?? null

  return (
    <div className="sandbox-canvas">
      {viewMode === 'model' ? (
        manifest?.components?.length
          ? <ArchitectureFlow manifest={manifest} height="100%" onNodeClick={setSelectedCompId} />
          : <EmptyState />
      ) : viewMode === 'code' ? (
        <CodeSandbox manifest={manifest} />
      ) : (
        <TraceView manifest={manifest} />
      )}

      <NodeInfoPopup
        component={selectedComponent}
        manifest={manifest}
        onClose={() => setSelectedCompId(null)}
      />
    </div>
  )
}
