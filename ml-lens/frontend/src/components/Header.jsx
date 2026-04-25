import React from 'react'
import AsteriskSpinner from './AsteriskSpinner'

export default function Header({ viewMode, setViewMode, onRunTraversal, traversalLoading, onGoEval, onExport, onGoHome, manifest }) {
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
        
        {/* Integrated View Toggle */}
        <div className="header-view-toggle">
          <button 
            className={`header-toggle-item ${viewMode === 'model' ? 'active' : ''}`}
            onClick={() => setViewMode('model')}
          >
            <span className="toggle-icon">㗊</span> Model
          </button>
          <button 
            className={`header-toggle-item ${viewMode === 'code' ? 'active' : ''}`}
            onClick={() => setViewMode('code')}
          >
            <span className="toggle-icon">{"</>"}</span> Code
          </button>
        </div>

        <div className="header-actions">
          <button
            className="btn-ghost header-traversal-btn"
            onClick={onRunTraversal}
            disabled={traversalLoading}
          >
            {traversalLoading
              ? <><AsteriskSpinner size={13} color="#4B5E78" />Running…</>
              : 'Run Traversal'
            }
          </button>
          {onGoEval && (
            <button className="btn-ghost" onClick={onGoEval}>Eval Results</button>
          )}
          <button className="btn-primary" onClick={onExport} disabled={!onExport}>Export</button>
        </div>
      </div>
    </header>
  )
}
