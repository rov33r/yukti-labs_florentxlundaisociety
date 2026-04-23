/**
 * Convert a ComponentManifest into a hierarchical React Flow graph.
 * Uses a vertical Sugiyama-style layout approach:
 * 1. Calculate vertical 'ranks' based on dependency depth.
 * 2. Center nodes horizontally within each rank.
 * 3. Standardize spacing for a clean top-to-bottom hierarchy.
 */

const KIND_EMOJI = {
  input_embedding:    '🔢',
  positional_encoding:'📍',
  linear_projection:  '➡',
  attention:          '🎯',
  multi_head_attention:'🎯',
  feedforward:        '⚡',
  layernorm:          '📐',
  rmsnorm:            '📐',
  residual:           '🔁',
  softmax:            '📊',
  masking:            '🔒',
  output_head:        '📤',
  other:              '🔷',
}

const KIND_STYLE = {
  input_embedding:    { background: '#EEF3FA', border: '1px solid #1E3A5F',  fontWeight: 600 },
  positional_encoding:{ background: '#EEF3FA', border: '1px solid #1E3A5F',  fontWeight: 600 },
  linear_projection:  { background: '#F5F5F5', border: '1px solid #9CA3AF' },
  attention:          { background: '#EDF7ED', border: '1px solid #16A34A',  fontWeight: 600 },
  multi_head_attention:{ background: '#EDF7ED', border: '2px solid #16A34A', fontWeight: 700 },
  feedforward:        { background: '#F5F5F5', border: '1px solid #9CA3AF' },
  layernorm:          { background: '#FDFCE9', border: '1px solid #CA8A04' },
  rmsnorm:            { background: '#FDFCE9', border: '1px solid #CA8A04' },
  residual:           { background: '#EEF3FA', border: '2px solid #1E3A5F',  fontWeight: 700 },
  softmax:            { background: '#FFF7ED', border: '1px solid #F97316' },
  masking:            { background: '#FFF1F2', border: '1px solid #F43F5E' },
  output_head:        { background: '#EEF3FA', border: '1px solid #1E3A5F',  fontWeight: 600 },
  other:              { background: 'white',   border: '1px solid #D6E4F0' },
}

const BASE_NODE_STYLE = {
  borderRadius: 8,
  padding: 10,
  fontFamily: 'Poppins, Arial, sans-serif',
  fontSize: 13,
  width: 200, // Fixed width for better centering
}

/** Topological sort — returns ordered list of component ids */
function topoSort(components) {
  const idSet = new Set(components.map((c) => c.id))
  const inDeg = {}
  const adj = {}
  components.forEach((c) => {
    inDeg[c.id] = 0
    adj[c.id] = []
  })
  components.forEach((c) => {
    ;(c.depends_on || []).forEach((dep) => {
      if (idSet.has(dep)) {
        adj[dep].push(c.id)
        inDeg[c.id]++
      }
    })
  })
  const queue = components.filter((c) => inDeg[c.id] === 0).map((c) => c.id)
  const sorted = []
  while (queue.length) {
    const id = queue.shift()
    sorted.push(id)
    adj[id].forEach((nxt) => {
      inDeg[nxt]--
      if (inDeg[nxt] === 0) queue.push(nxt)
    })
  }
  // Append any that didn't make it (cycles)
  components.forEach((c) => { if (!sorted.includes(c.id)) sorted.push(c.id) })
  return sorted
}

/** Assign (x, y) positions for a Vertical Hierarchy */
function assignPositions(components) {
  const sorted = topoSort(components)
  const compMap = Object.fromEntries(components.map((c) => [c.id, c]))
  const rank = {}
  
  // Calculate Rank (Vertical level)
  sorted.forEach((id) => {
    const deps = (compMap[id]?.depends_on || []).filter((d) => rank[d] !== undefined)
    rank[id] = deps.length ? Math.max(...deps.map((d) => rank[d])) + 1 : 0
  })

  // Group nodes by Rank
  const nodesByRank = {}
  sorted.forEach((id) => {
    const r = rank[id]
    if (!nodesByRank[r]) nodesByRank[r] = []
    nodesByRank[r].push(id)
  })

  const NODE_W = 220
  const NODE_H = 80
  const HORIZ_GAP = 250
  const VERT_GAP = 140

  // Assign X and Y
  Object.keys(nodesByRank).forEach((r) => {
    const idsInRank = nodesByRank[r]
    const totalW = (idsInRank.length - 1) * HORIZ_GAP
    const xStart = -totalW / 2 // Center the rank horizontally

    idsInRank.forEach((id, index) => {
      compMap[id]._pos = {
        x: xStart + index * HORIZ_GAP,
        y: parseInt(r) * VERT_GAP
      }
    })
  })

  return compMap
}

export function manifestToFlow(manifest) {
  if (!manifest?.components?.length) return { nodes: [], edges: [] }

  const compMap = assignPositions(manifest.components)
  const idSet = new Set(manifest.components.map((c) => c.id))

  const nodes = manifest.components.map((comp) => ({
    id: comp.id,
    position: comp._pos ?? { x: 0, y: 0 },
    data: {
      label: `${KIND_EMOJI[comp.kind] ?? '🔷'} ${comp.name}`,
      component: comp,
      manifest,
    },
    style: { ...BASE_NODE_STYLE, ...(KIND_STYLE[comp.kind] ?? KIND_STYLE.other) },
    // Use input/output types for handles
    type: comp.depends_on?.length === 0 ? 'input' : undefined,
  }))

  // Determine output nodes (no outgoing edges)
  const hasOutgoing = new Set()
  manifest.components.forEach((c) => {
    ;(c.depends_on || []).filter((d) => idSet.has(d)).forEach((d) => hasOutgoing.add(d))
  })
  
  nodes.forEach((n) => {
    if (!hasOutgoing.has(n.id) && n.type !== 'input') {
      n.type = 'output'
    }
  })

  const edges = []
  manifest.components.forEach((comp) => {
    ;(comp.depends_on || []).forEach((dep) => {
      if (!idSet.has(dep)) return
      
      const isImportant = ['attention', 'multi_head_attention', 'residual'].includes(comp.kind)
      
      edges.push({
        id: `e-${dep}-${comp.id}`,
        source: dep,
        target: comp.id,
        animated: isImportant,
        style: {
          stroke: isImportant ? '#1E3A5F' : '#7A93B0',
          strokeWidth: isImportant ? 2 : 1,
          strokeDasharray: comp.kind === 'masking' ? '5,5' : undefined,
        },
      })
    })
  })

  return { nodes, edges }
}
