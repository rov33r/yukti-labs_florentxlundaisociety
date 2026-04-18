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
import NodeInfoPopup from './NodeInfoPopup'

const nodeBase = { borderRadius: 8, padding: 10, fontFamily: 'Poppins, Arial, sans-serif', fontSize: 13 }
const navyNode  = { ...nodeBase, background: '#EEF3FA', border: '1px solid #1E3A5F', fontWeight: 600 }
const navyStrong = { ...nodeBase, background: '#EEF3FA', border: '2px solid #1E3A5F', fontWeight: 700 }
const plainNode = { ...nodeBase, background: 'white', border: '1px solid #D6E4F0' }
const decNode   = { ...nodeBase, background: '#FFF7ED', border: '2px solid #F97316', fontWeight: 700 }

const mockNodes = [
  { id: '1',  type: 'input',  position: { x: 250, y: 0 },   data: { label: '📄 Input Tokens' },         style: navyNode },
  { id: '2',                  position: { x: 100, y: 120 },  data: { label: '🔢 Input Embedding' },       style: plainNode },
  { id: '3',                  position: { x: 400, y: 120 },  data: { label: '📍 Positional Encoding' },   style: plainNode },
  { id: '4',                  position: { x: 250, y: 250 },  data: { label: '🔁 Encoder (×6)' },          style: navyStrong },
  { id: '5',                  position: { x: 100, y: 380 },  data: { label: '🎯 Multi-Head Attention' },  style: plainNode },
  { id: '6',                  position: { x: 400, y: 380 },  data: { label: '⚡ Feed Forward' },           style: plainNode },
  { id: '7',                  position: { x: 250, y: 510 },  data: { label: '🔁 Decoder (×6)' },          style: decNode },
  { id: '8',                  position: { x: 100, y: 640 },  data: { label: '🎯 Masked Attention' },      style: plainNode },
  { id: '9',                  position: { x: 400, y: 640 },  data: { label: '🔗 Cross Attention' },       style: plainNode },
  { id: '10', type: 'output', position: { x: 250, y: 770 },  data: { label: '📊 Linear + Softmax' },      style: navyNode },
]

const mockEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#1E3A5F' } },
  { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#1E3A5F' } },
  { id: 'e2-4', source: '2', target: '4', style: { stroke: '#7A93B0' } },
  { id: 'e3-4', source: '3', target: '4', style: { stroke: '#7A93B0' } },
  { id: 'e4-5', source: '4', target: '5', style: { stroke: '#7A93B0' } },
  { id: 'e4-6', source: '4', target: '6', style: { stroke: '#7A93B0' } },
  { id: 'e5-7', source: '5', target: '7', style: { stroke: '#7A93B0' } },
  { id: 'e6-7', source: '6', target: '7', style: { stroke: '#7A93B0' } },
  { id: 'e4-9', source: '4', target: '9', animated: true, style: { stroke: '#F97316', strokeDasharray: '5,5' } },
  { id: 'e7-8', source: '7', target: '8', style: { stroke: '#7A93B0' } },
  { id: 'e7-9', source: '7', target: '9', style: { stroke: '#7A93B0' } },
  { id: 'e8-10', source: '8', target: '10', style: { stroke: '#7A93B0' } },
  { id: 'e9-10', source: '9', target: '10', style: { stroke: '#7A93B0' } },
]

export default function Sandbox() {
  const [nodes, setNodes, onNodesChange] = useNodesState(mockNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(mockEdges)
  const [selectedNode, setSelectedNode] = useState(null)

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode(node)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  return (
    <div className="sandbox-canvas">
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
        <MiniMap
          nodeStrokeColor="#1E3A5F"
          nodeColor="#EEF3FA"
          maskColor="rgba(250, 250, 250, 0.8)"
        />
        <Background color="#E5E5E5" gap={16} />
      </ReactFlow>

      <NodeInfoPopup node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  )
}
