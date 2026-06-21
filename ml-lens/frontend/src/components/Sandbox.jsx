import React, { useState } from 'react'
import { MousePointer2, Code2, Activity } from 'lucide-react'
import ArchitectureFlow from './ArchitectureFlow'
import NodeInfoPopup from './NodeInfoPopup'
import CodeSandbox from './CodeSandbox'
import TraceView from './TraceView'

const EMPTY_STEPS = [
  {
    icon: MousePointer2,
    label: 'Click any node',
    desc: 'Opens the component inspector with equations, tensor shapes, and the paper quote that describes it',
  },
  {
    icon: Code2,
    label: 'Switch to Code view',
    desc: "Generates a PyTorch implementation grounded in the locked schema, not from the LLM's memory",
  },
  {
    icon: Activity,
    label: 'Switch to Trace view',
    desc: 'Runs the forward pass step by step, showing exactly how tensor shapes change through the network',
  },
]

function EmptyState({ onGoHome }) {
  return (
    <div className="sandbox-empty">
      <p className="sandbox-empty-title">Load a paper to start exploring</p>
      <div className="sandbox-empty-steps">
        {EMPTY_STEPS.map(({ icon: Icon, label, desc }, i) => (
          <div key={label} className="sandbox-empty-step">
            <div className="sandbox-empty-step-num">{i + 1}</div>
            <div className="sandbox-empty-step-body">
              <span className="sandbox-empty-step-label">
                <Icon size={13} style={{ verticalAlign: 'middle', marginRight: 5 }} />
                {label}
              </span>
              <span className="sandbox-empty-step-desc">{desc}</span>
            </div>
          </div>
        ))}
      </div>
      {onGoHome && (
        <button className="btn-ghost sandbox-empty-home-btn" onClick={onGoHome}>
          ← Load a paper first
        </button>
      )}
    </div>
  )
}

export default function Sandbox({ manifest, viewMode, onGoHome }) {
  const [selectedCompId, setSelectedCompId] = useState(null)
  const [sandboxTab, setSandboxTab] = useState('graph') // 'graph' | 'manifest'
  const selectedComponent = manifest?.components?.find(c => c.id === selectedCompId) ?? null

  const manifestJson = manifest
    ? JSON.stringify(manifest, null, 2)
    : '// No manifest loaded yet'

  return (
    <div className="sandbox-canvas">
      {/* Manifest JSON tab strip — only shown when a manifest is loaded */}
      {manifest?.components?.length > 0 && (
        <div className="sandbox-tab-strip">
          <button
            className={`sandbox-tab ${sandboxTab === 'graph' ? 'sandbox-tab--active' : ''}`}
            onClick={() => setSandboxTab('graph')}
          >
            Graph
          </button>
          <button
            className={`sandbox-tab ${sandboxTab === 'manifest' ? 'sandbox-tab--active' : ''}`}
            onClick={() => setSandboxTab('manifest')}
          >
            Manifest JSON
            <span className="sandbox-tab-badge">{manifest.components.length}</span>
          </button>
        </div>
      )}

      {sandboxTab === 'manifest' && manifest ? (
        <div className="manifest-viewer">
          <div className="manifest-viewer-toolbar">
            <span className="manifest-viewer-label">
              {manifest.paper?.title ?? 'Manifest'} — {manifest.components?.length ?? 0} components
            </span>
            <button
              className="manifest-copy-btn"
              onClick={() => navigator.clipboard.writeText(manifestJson)}
            >
              Copy JSON
            </button>
          </div>
          <pre className="manifest-json">{manifestJson}</pre>
        </div>
      ) : viewMode === 'model' ? (
        manifest?.components?.length
          ? <ArchitectureFlow manifest={manifest} height="100%" onNodeClick={setSelectedCompId} />
          : <EmptyState onGoHome={onGoHome} />
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
