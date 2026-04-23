import React from 'react'
import AsteriskSpinner from './AsteriskSpinner'

export default function Header({ viewMode, setViewMode, onRunTraversal, traversalLoading }) {
  return (
    <header className="header">
      <div className="header-container">
        <h1 className="logo">Yukti</h1>
        
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
          <button className="btn-primary">Export</button>
        </div>
      </div>
    </header>
  )
}
