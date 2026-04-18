import React, { useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

const KIND_COLORS = {
  input_embedding:      { bg: '#EFF6FF', border: '#3B82F6', text: '#1D4ED8' },
  positional_encoding:  { bg: '#F0FDF4', border: '#22C55E', text: '#15803D' },
  multi_head_attention: { bg: '#FDF4FF', border: '#A855F7', text: '#7E22CE' },
  attention:            { bg: '#FDF4FF', border: '#A855F7', text: '#7E22CE' },
  feedforward:          { bg: '#FFF7ED', border: '#F97316', text: '#C2410C' },
  layernorm:            { bg: '#F0F9FF', border: '#0EA5E9', text: '#0369A1' },
  rmsnorm:              { bg: '#F0F9FF', border: '#0EA5E9', text: '#0369A1' },
  residual:             { bg: '#FAFAFA', border: '#6B7280', text: '#374151' },
  softmax:              { bg: '#FFF1F2', border: '#F43F5E', text: '#BE123C' },
  masking:              { bg: '#FFFBEB', border: '#EAB308', text: '#92400E' },
  linear_projection:    { bg: '#F0FDFA', border: '#14B8A6', text: '#0F766E' },
  output_head:          { bg: '#FEF2F2', border: '#EF4444', text: '#991B1B' },
  other:                { bg: '#F9FAFB', border: '#9CA3AF', text: '#4B5563' },
}

function fmtParams(n) {
  if (!n) return null
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M params`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K params`
  return `${n} params`
}

function ComponentNode({ data }) {
  const colors = KIND_COLORS[data.kind] || KIND_COLORS.other
  const isActive = data.activeStep?.component_id === data.id
  const step = data.steps?.find(s => s.component_id === data.id)
  const paramLabel = step ? fmtParams(step.parameter_count) : null

  return (
    <div style={{
      background: colors.bg,
      border: `2px solid ${isActive ? '#0D9488' : colors.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      minWidth: 170,
      maxWidth: 210,
      boxShadow: isActive ? '0 0 0 3px rgba(13,148,136,0.3)' : '0 1px 3px rgba(0,0,0,0.08)',
      transition: 'all 0.25s ease',
      cursor: 'pointer',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: colors.border }} />

      <div style={{ fontSize: 10, fontWeight: 700, color: colors.text, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
        {data.kind.replace(/_/g, ' ')}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A', lineHeight: 1.3, marginBottom: 4 }}>
        {data.label}
      </div>

      {/* Shape pill when active */}
      {isActive && step && (
        <div style={{ fontSize: 10, fontFamily: 'monospace', color: '#0D9488', marginBottom: 4 }}>
          [{step.input_symbolic?.join(', ')}] → [{step.output_symbolic?.join(', ')}]
        </div>
      )}

      {/* Param count badge */}
      {paramLabel && (
        <div style={{
          display: 'inline-block',
          fontSize: 9, fontWeight: 700,
          background: isActive ? '#0D9488' : '#F3F4F6',
          color: isActive ? 'white' : '#6B7280',
          padding: '1px 6px', borderRadius: 9, marginTop: 2,
          transition: 'all 0.25s ease',
        }}>
          {paramLabel}
        </div>
      )}

      {/* Key insight on active */}
      {isActive && step?.key_insight && (
        <div style={{ fontSize: 10, color: '#374151', marginTop: 6, fontStyle: 'italic', lineHeight: 1.4 }}>
          {step.key_insight}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: colors.border }} />
    </div>
  )
}

const nodeTypes = { component: ComponentNode }

function buildLayout(components) {
  const idMap = Object.fromEntries(components.map(c => [c.id, c]))
  const levels = {}

  const visited = new Set()
  function visit(id, depth) {
    if (levels[id] === undefined || levels[id] < depth) levels[id] = depth
    if (visited.has(id)) return
    visited.add(id)
    const comp = idMap[id]
    if (!comp) return
    components.forEach(c => {
      if (c.depends_on.includes(id)) visit(c.id, depth + 1)
    })
  }
  const roots = components.filter(c => c.depends_on.length === 0)
  roots.forEach(c => visit(c.id, 0))
  components.forEach(c => { if (levels[c.id] === undefined) levels[c.id] = 0 })

  const byLevel = {}
  components.forEach(c => {
    const lv = levels[c.id]
    if (!byLevel[lv]) byLevel[lv] = []
    byLevel[lv].push(c.id)
  })

  const pos = {}
  Object.entries(byLevel).forEach(([lv, ids]) => {
    ids.forEach((id, i) => {
      pos[id] = { x: (i - (ids.length - 1) / 2) * 250, y: Number(lv) * 170 }
    })
  })
  return pos
}

export default function ArchitectureFlow({ manifest, trace, activeStepIndex, onNodeClick }) {
  const positions = useMemo(() => buildLayout(manifest.components), [manifest.components])
  const activeStep = trace?.steps?.[activeStepIndex] ?? null

  const nodes = useMemo(() => manifest.components.map(c => ({
    id: c.id,
    type: 'component',
    position: positions[c.id] || { x: 0, y: 0 },
    data: { id: c.id, label: c.name, kind: c.kind, activeStep, steps: trace?.steps ?? [] },
  })), [manifest.components, positions, activeStep, trace])

  const edges = useMemo(() => {
    const result = []
    manifest.components.forEach(c => {
      c.depends_on.forEach(dep => {
        result.push({
          id: `${dep}->${c.id}`,
          source: dep, target: c.id,
          animated: activeStep != null,
          style: { stroke: '#0D9488', strokeWidth: 2 },
          markerEnd: { type: 'arrowclosed', color: '#0D9488' },
        })
      })
    })
    return result
  }, [manifest.components, activeStep])

  const [, , onNodesChange] = useNodesState(nodes)
  const [, , onEdgesChange] = useEdgesState(edges)

  return (
    <div style={{ width: '100%', height: 500, borderRadius: 12, overflow: 'hidden', border: '1px solid #E5E5E5' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.35 }}
      >
        <Background color="#F3F4F6" gap={20} />
        <Controls />
        <MiniMap nodeColor={n => KIND_COLORS[n.data?.kind]?.border ?? '#9CA3AF'} pannable zoomable />
      </ReactFlow>
    </div>
  )
}
