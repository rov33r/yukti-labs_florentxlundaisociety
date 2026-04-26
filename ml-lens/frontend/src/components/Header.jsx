import React from 'react'
import { Network, Code2, Activity, Download } from 'lucide-react'

const VIEW_TABS = [
  { id: 'model', icon: Network,   label: 'Model',  sub: 'Architecture diagram' },
  { id: 'code',  icon: Code2,     label: 'Code',   sub: 'Generated PyTorch' },
  { id: 'trace', icon: Activity,  label: 'Trace',  sub: 'Forward pass' },
]

export default function Header({ viewMode, setViewMode, onGoEval, onExport, onGoHome, manifest }) {
  const arxivId = manifest?.paper?.arxiv_id
  return (
    <header className="header">
      <div className="header-container">
        <div className="header-logo-group">
          <h1 className={`logo ${onGoHome ? 'logo-clickable' : ''}`} onClick={onGoHome}>Yukti</h1>
          {arxivId && (
            <span className="header-breadcrumb">
              <span className="header-breadcrumb-sep">/</span>
              <span className="header-breadcrumb-id">{arxivId}</span>
            </span>
          )}
        </div>

        <div className="header-view-toggle">
          {VIEW_TABS.map(({ id, icon: Icon, label, sub }) => (
            <button
              key={id}
              className={`header-toggle-item ${viewMode === id ? 'active' : ''}`}
              onClick={() => setViewMode(id)}
            >
              <span className="toggle-icon-wrap">
                <Icon size={14} />
              </span>
              <span className="toggle-label-wrap">
                <span className="toggle-label">{label}</span>
                <span className="toggle-sub">{sub}</span>
              </span>
            </button>
          ))}
        </div>

        <div className="header-actions">
          {onGoEval && (
            <button className="btn-ghost" onClick={onGoEval}>Eval Results</button>
          )}
          <button
            className="btn-primary header-export-btn"
            onClick={onExport}
            disabled={!onExport}
            title="Download the locked schema as a .json file"
          >
            <Download size={13} />
            Save Manifest
          </button>
        </div>
      </div>
    </header>
  )
}
