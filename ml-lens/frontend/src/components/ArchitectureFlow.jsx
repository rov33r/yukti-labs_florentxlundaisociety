import React, { useCallback, useMemo } from 'react'
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

function ComponentNode({ data }) {
  const colors = KIND_COLORS[data.kind] || KIND_COLORS.other
  const isActive = data.activeStep?.component_id === data.id
  const stepData = data.steps?.find(s => s.component_id === data.id)

  return (
    <div style={{
      background: colors.bg,
      border: `2px solid ${isActive ? '#0D9488' : colors.border}`,
      borderRadius: 10,
      padding: '12px 16px',
      minWidth: 180,
      maxWidth: 220,
      boxShadow: isActive ? '0 0 0 3px rgba(13,148,136,0.25)' : '0 1px 3px rgba(0,0,0,0.08)',
      transition: 'all 0.2s ease',
      cursor: 'pointer',
    }}>
      <Handle type="target" position={Position.Top} style={{ background: colors.border }} />
      <div style={{ fontSize: 10, fontWeight: 700, color: colors.text, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {data.kind.replace(/_/g, ' ')}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#1A1A1A', lineHeight: 1.3 }}>
        {data.label}
      </div>
      {stepData && (
        <div style={{ fontSize: 10, color: '#6B7280', marginTop: 6, fontStyle: 'italic', lineHeight: 1.4 }}>
          {stepData.key_insight}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: colors.border }} />
    </div>
  )
}

const nodeTypes = { component: ComponentNode }

function buildLayout(components) {
  const idMap = Object.fromEntries(components.map(c => [c.id, c]))
  const inDegree = Object.fromEntries(components.map(c => [c.id, 0]))
  components.forEach(c => c.depends_on.forEach(dep => { if (inDegree[c.id] !== undefined) inDegree[c.id]++ }))

  const levels = {}
  const queue = components.filter(c => inDegree[c.id] === 0).map(c => c.id)
  queue.forEach(id => { levels[id] = 0 })

  const visited = new Set(queue)
  while (queue.length) {
    const curr = queue.shift()
    const comp = idMap[curr]
    if (!comp) continue
    components.forEach(c => {
      if (c.depends_on.includes(curr) && !visited.has(c.id)) {
        levels[c.id] = Math.max(levels[c.id] || 0, (levels[curr] || 0) + 1)
        visited.add(c.id)
        queue.push(c.id)
      }
    })
  }

  const levelGroups = {}
  components.forEach(c => {
    const lv = levels[c.id] ?? 0
    if (!levelGroups[lv]) levelGroups[lv] = []
    levelGroups[lv].push(c.id)
  })

  const positions = {}
  Object.entries(levelGroups).forEach(([lv, ids]) => {
    ids.forEach((id, i) => {
      positions[id] = {
        x: i * 240 - ((ids.length - 1) * 120),
        y: Number(lv) * 160,
      }
    })
  })

  return positions
}

export default function ArchitectureFlow({ manifest, trace, activeStepIndex, onNodeClick }) {
  const positions = useMemo(() => buildLayout(manifest.components), [manifest.components])
  const activeStep = trace?.steps?.[activeStepIndex] ?? null

  const nodes = useMemo(() => manifest.components.map(c => ({
    id: c.id,
    type: 'component',
    position: positions[c.id] || { x: 0, y: 0 },
    data: {
      id: c.id,
      label: c.name,
      kind: c.kind,
      activeStep,
      steps: trace?.steps ?? [],
    },
  })), [manifest.components, positions, activeStep, trace])

  const edges = useMemo(() => {
    const result = []
    manifest.components.forEach(c => {
      c.depends_on.forEach(dep => {
        result.push({
          id: `${dep}->${c.id}`,
          source: dep,
          target: c.id,
          animated: activeStep != null,
          style: { stroke: '#0D9488', strokeWidth: 2 },
        })
      })
    })
    return result
  }, [manifest.components, activeStep])

  const [rfNodes, , onNodesChange] = useNodesState(nodes)
  const [rfEdges, , onEdgesChange] = useEdgesState(edges)

  return (
    <div style={{ width: '100%', height: 480, borderRadius: 12, overflow: 'hidden', border: '1px solid #E5E5E5' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
      >
        <Background color="#F3F4F6" gap={20} />
        <Controls />
        <MiniMap nodeColor={n => KIND_COLORS[n.data?.kind]?.border ?? '#9CA3AF'} />
      </ReactFlow>
    </div>
  )
}
