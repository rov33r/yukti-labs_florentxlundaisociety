import React, { useCallback, useState } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { computeDiff } from '../api/client'
import { useDiffStore } from '../store/diffStore'
import DiffPanel from './DiffPanel'

const mockNodes = [
  {
    id: '1',
    type: 'input',
    position: { x: 250, y: 0 },
    data: { label: '📄 Input Tokens' },
    style: { background: '#F0FDFA', border: '1px solid #0D9488', borderRadius: 8, padding: 10, fontWeight: 600 }
  },
  {
    id: '2',
    position: { x: 100, y: 120 },
    data: { label: '🔢 Input Embedding' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '3',
    position: { x: 400, y: 120 },
    data: { label: '📍 Positional Encoding' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '4',
    position: { x: 250, y: 250 },
    data: { label: '🔁 Encoder (×6)' },
    style: { background: '#F0FDFA', border: '2px solid #0D9488', borderRadius: 8, padding: 10, fontWeight: 600 }
  },
  {
    id: '5',
    position: { x: 100, y: 380 },
    data: { label: '🎯 Multi-Head Attention' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '6',
    position: { x: 400, y: 380 },
    data: { label: '⚡ Feed Forward' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '7',
    position: { x: 250, y: 510 },
    data: { label: '🔁 Decoder (×6)' },
    style: { background: '#FFF7ED', border: '2px solid #F97316', borderRadius: 8, padding: 10, fontWeight: 600 }
  },
  {
    id: '8',
    position: { x: 100, y: 640 },
    data: { label: '🎯 Masked Attention' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '9',
    position: { x: 400, y: 640 },
    data: { label: '🔗 Cross Attention' },
    style: { background: 'white', border: '1px solid #E5E5E5', borderRadius: 8, padding: 10 }
  },
  {
    id: '10',
    type: 'output',
    position: { x: 250, y: 770 },
    data: { label: '📊 Linear + Softmax' },
    style: { background: '#F0FDFA', border: '1px solid #0D9488', borderRadius: 8, padding: 10, fontWeight: 600 }
  },
]

const mockEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#0D9488' } },
  { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#0D9488' } },
  { id: 'e2-4', source: '2', target: '4', style: { stroke: '#6B6B6B' } },
  { id: 'e3-4', source: '3', target: '4', style: { stroke: '#6B6B6B' } },
  { id: 'e4-5', source: '4', target: '5', style: { stroke: '#6B6B6B' } },
  { id: 'e4-6', source: '4', target: '6', style: { stroke: '#6B6B6B' } },
  { id: 'e5-7', source: '5', target: '7', style: { stroke: '#6B6B6B' } },
  { id: 'e6-7', source: '6', target: '7', style: { stroke: '#6B6B6B' } },
  { id: 'e4-9', source: '4', target: '9', animated: true, style: { stroke: '#F97316', strokeDasharray: '5,5' } },
  { id: 'e7-8', source: '7', target: '8', style: { stroke: '#6B6B6B' } },
  { id: 'e7-9', source: '7', target: '9', style: { stroke: '#6B6B6B' } },
  { id: 'e8-10', source: '8', target: '10', style: { stroke: '#6B6B6B' } },
  { id: 'e9-10', source: '9', target: '10', style: { stroke: '#6B6B6B' } },
]

export default function Sandbox() {
  const [nodes, setNodes, onNodesChange] = useNodesState(mockNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(mockEdges)
  const [numHeads, setNumHeads] = useState(8)
  const [diffResult, setDiffResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { setDiff } = useDiffStore()

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  const handleRunDiff = async () => {
    setLoading(true)
    setError(null)
    try {
      const manifest = {
        paper: {
          arxiv_id: "1706.03762",
          title: "Attention Is All You Need",
          authors: [],
          abstract: null,
          published: null,
          pdf_url: null
        },
        components: [],
        tensor_contracts: [],
        invariants: [],
        symbol_table: {},
        notes: null,
        locked: true
      }
      const baseParams = { d_model: 512, num_heads: 8, d_ff: 2048, seq_len: 8 }
      const deltas = [{ component_id: "attention", param: "num_heads", old_value: 8, new_value: numHeads }]
      const result = await computeDiff(manifest, baseParams, deltas)
      setDiffResult(result)
      setDiff(result.schema_diff)
      updateNodeColorsForDiff(result.schema_diff)
    } catch (err) {
      setError(err.message || 'Failed to compute diff')
    } finally {
      setLoading(false)
    }
  }

  const updateNodeColorsForDiff = (schemaDiff) => {
    const changedIds = new Set(schemaDiff.component_diffs.filter(d => d.changed).map(d => d.component_id))
    setNodes((ns) =>
      ns.map((n) => {
        if (changedIds.has(n.id === '5' ? 'attention' : null)) {
          return {
            ...n,
            style: { ...n.style, background: '#FAEEDA', border: '1.5px solid #854F0B' }
          }
        }
        return n
      })
    )
  }

  return (
    <div className="sandbox-page">
      <div className="sandbox-header">
        <div>
          <h2>Component Sandbox</h2>
          <p className="page-subtitle">Attention Is All You Need — Transformer architecture</p>
        </div>
        <div className="sandbox-badges">
          <span className="badge badge-completed">Mock Data</span>
        </div>
      </div>

      <div className="sandbox-controls">
        <div className="slider-control">
          <label>
            num_heads: {numHeads}
            <input
              type="range"
              min="1"
              max="16"
              step="1"
              value={numHeads}
              onChange={(e) => setNumHeads(Number(e.target.value))}
              style={{ marginLeft: '12px' }}
            />
          </label>
        </div>
        <button
          className="btn-primary"
          onClick={handleRunDiff}
          disabled={loading}
        >
          {loading ? 'Computing diff…' : 'Run diff against schema'}
        </button>
        {error && <p style={{ color: 'red', marginTop: '8px' }}>{error}</p>}
      </div>

      <div className="sandbox-legend">
        <span className="legend-item"><span className="legend-dot teal"></span>Encoder</span>
        <span className="legend-item"><span className="legend-dot orange"></span>Decoder</span>
        <span className="legend-item"><span className="legend-dot gray"></span>Sub-layer</span>
        <span className="legend-item"><span className="legend-line animated"></span>Data flow</span>
        <span className="legend-item"><span className="legend-line cross"></span>Cross attention</span>
      </div>

      <div className="flow-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Controls />
          <MiniMap
            nodeStrokeColor="#0D9488"
            nodeColor="#F0FDFA"
            maskColor="rgba(250, 250, 250, 0.8)"
          />
          <Background color="#E5E5E5" gap={16} />
        </ReactFlow>
      </div>

      {diffResult && <DiffPanel schemaDiff={diffResult.schema_diff} />}
    </div>
  )
}
