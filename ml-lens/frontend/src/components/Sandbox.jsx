import React, { useCallback, useState, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  Panel,
  useNodesState,
  useEdgesState,
  addEdge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import NodeInfoPopup from './NodeInfoPopup'
import TraversalPanel from './TraversalPanel'
import CodeSandbox from './CodeSandbox'
import { manifestToFlow } from '../utils/manifestToFlow'

// ── Fallback hardcoded demo (Attention Is All You Need) ──────────────────────
const nodeBase = { borderRadius: 8, padding: 10, fontFamily: 'Poppins, Arial, sans-serif', fontSize: 13 }
const navyNode   = { ...nodeBase, background: '#EEF3FA', border: '1px solid #1E3A5F',  fontWeight: 600 }
const navyStrong = { ...nodeBase, background: '#EEF3FA', border: '2px solid #1E3A5F',  fontWeight: 700 }
const plainNode  = { ...nodeBase, background: 'white',   border: '1px solid #D6E4F0' }
const decNode    = { ...nodeBase, background: '#FFF7ED', border: '2px solid #F97316',  fontWeight: 700 }

const DEMO_NODES = [
  { id: '1',  type: 'input',  position: { x: 250, y: 0 },   data: { label: '📄 Input Tokens' },        style: navyNode },
  { id: '2',                  position: { x: 100, y: 120 },  data: { label: '🔢 Input Embedding' },      style: plainNode },
  { id: '3',                  position: { x: 400, y: 120 },  data: { label: '📍 Positional Encoding' },  style: plainNode },
  { id: '4',                  position: { x: 250, y: 250 },  data: { label: '🔁 Encoder (×6)' },         style: navyStrong },
  { id: '5',                  position: { x: 100, y: 380 },  data: { label: '🎯 Multi-Head Attention' }, style: plainNode },
  { id: '6',                  position: { x: 400, y: 380 },  data: { label: '⚡ Feed Forward' },          style: plainNode },
  { id: '7',                  position: { x: 250, y: 510 },  data: { label: '🔁 Decoder (×6)' },         style: decNode },
  { id: '8',                  position: { x: 100, y: 640 },  data: { label: '🎯 Masked Attention' },     style: plainNode },
  { id: '9',                  position: { x: 400, y: 640 },  data: { label: '🔗 Cross Attention' },      style: plainNode },
  { id: '10', type: 'output', position: { x: 250, y: 770 },  data: { label: '📊 Linear + Softmax' },     style: navyNode },
]

const DEMO_EDGES = [
  { id: 'e1-2',  source: '1', target: '2',  animated: true, style: { stroke: '#1E3A5F' } },
  { id: 'e1-3',  source: '1', target: '3',  animated: true, style: { stroke: '#1E3A5F' } },
  { id: 'e2-4',  source: '2', target: '4',  style: { stroke: '#7A93B0' } },
  { id: 'e3-4',  source: '3', target: '4',  style: { stroke: '#7A93B0' } },
  { id: 'e4-5',  source: '4', target: '5',  style: { stroke: '#7A93B0' } },
  { id: 'e4-6',  source: '4', target: '6',  style: { stroke: '#7A93B0' } },
  { id: 'e5-7',  source: '5', target: '7',  style: { stroke: '#7A93B0' } },
  { id: 'e6-7',  source: '6', target: '7',  style: { stroke: '#7A93B0' } },
  { id: 'e4-9',  source: '4', target: '9',  animated: true, style: { stroke: '#F97316', strokeDasharray: '5,5' } },
  { id: 'e7-8',  source: '7', target: '8',  style: { stroke: '#7A93B0' } },
  { id: 'e7-9',  source: '7', target: '9',  style: { stroke: '#7A93B0' } },
  { id: 'e8-10', source: '8', target: '10', style: { stroke: '#7A93B0' } },
  { id: 'e9-10', source: '9', target: '10', style: { stroke: '#7A93B0' } },
]
// ─────────────────────────────────────────────────────────────────────────────

export default function Sandbox({
  manifest,
  viewMode,
  hyperparams,
  onParamChange,
  onParamReset,
  traversalResult,
  traversalError,
  onCloseTraversal,
}) {
  // Derive initial nodes/edges from manifest (or demo fallback)
  const { initialNodes, initialEdges } = useMemo(() => {
    if (manifest?.components?.length) {
      return { initialNodes: manifestToFlow(manifest).nodes, initialEdges: manifestToFlow(manifest).edges }
    }
    return { initialNodes: DEMO_NODES, initialEdges: DEMO_EDGES }
  }, [manifest])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState(null)

  // Re-build the graph whenever the manifest changes (e.g. new paper loaded)
  useEffect(() => {
    if (manifest?.components?.length) {
      const { nodes: n, edges: e } = manifestToFlow(manifest)
      setNodes(n)
      setEdges(e)
    } else {
      setNodes(DEMO_NODES)
      setEdges(DEMO_EDGES)
    }
    setSelectedNode(null)
  }, [manifest])

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  const onNodeClick = useCallback((_event, node) => setSelectedNode(node), [])
  const onPaneClick = useCallback(() => setSelectedNode(null), [])

  const isManifestMode = !!(manifest?.components?.length)

  return (
    <div className="sandbox-canvas">
      {viewMode === 'model' ? (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          fitView
        >
          <Controls />
          <Background color="#E5E5E5" gap={16} />

          {/* Paper banner in manifest mode */}
          {isManifestMode && (
            <Panel position="top-center">
              <div className="sandbox-top-controls">
                <div className="sandbox-paper-banner">
                  <span className="sandbox-paper-arxiv">{manifest.paper?.arxiv_id}</span>
                  <span className="sandbox-paper-title">{manifest.paper?.title}</span>
                  <span className="sandbox-paper-count">{manifest.components.length} components</span>
                </div>
              </div>
            </Panel>
          )}

          <Panel position="bottom-right">
            {isManifestMode ? (
              <div className="sandbox-legend">
                <div className="legend-row"><span className="legend-node" style={{ background: '#EDF7ED', border: '2px solid #16A34A' }} /><span className="legend-label">Attention</span></div>
                <div className="legend-row"><span className="legend-node" style={{ background: '#FDFCE9', border: '1px solid #CA8A04' }} /><span className="legend-label">Norm</span></div>
                <div className="legend-row"><span className="legend-node" style={{ background: '#FFF1F2', border: '1px solid #F43F5E' }} /><span className="legend-label">Masking</span></div>
                <div className="legend-row"><span className="legend-node" style={{ background: '#EEF3FA', border: '1px solid #1E3A5F' }} /><span className="legend-label">Embedding / Head</span></div>
                <div className="legend-row"><span className="legend-node plain" /><span className="legend-label">Other</span></div>
              </div>
            ) : (
              <div className="sandbox-legend">
                <div className="legend-row"><span className="legend-node navy" /><span className="legend-label">Encoder</span></div>
                <div className="legend-row"><span className="legend-node orange" /><span className="legend-label">Decoder</span></div>
                <div className="legend-row"><span className="legend-node plain" /><span className="legend-label">Sub-layer</span></div>
                <div className="legend-divider" />
                <div className="legend-row"><span className="legend-edge animated" /><span className="legend-label">Data flow</span></div>
                <div className="legend-row"><span className="legend-edge dashed" /><span className="legend-label">Cross attention</span></div>
              </div>
            )}
          </Panel>
        </ReactFlow>
      ) : (
        <CodeSandbox manifest={manifest} />
      )}

      <NodeInfoPopup
        node={selectedNode}
        params={selectedNode ? hyperparams[selectedNode.id] : null}
        onParamChange={onParamChange}
        onParamReset={onParamReset}
        onClose={() => setSelectedNode(null)}
        isManifestMode={isManifestMode}
      />

      {(traversalResult || traversalError) && (
        <TraversalPanel
          result={traversalResult}
          error={traversalError}
          onClose={onCloseTraversal}
        />
      )}
    </div>
  )
}
