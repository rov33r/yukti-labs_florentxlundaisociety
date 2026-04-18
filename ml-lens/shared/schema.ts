// TypeScript schema definitions for ML Lens
// Mirrors the Pydantic models from backend/schema/models.py

export interface PaperMetadata {
  arxiv_id: string
  title: string
  authors: string[]
  abstract?: string
  published?: string
  pdf_url?: string
}

export interface StateSnapshot {
  component_id: string
  input_shape: string
  output_shape: string
  input_sample: number[]
  output_sample: number[]
  operation_note: string
}

export interface TraversalTrace {
  paper_id: string
  params: Record<string, number>
  snapshots: StateSnapshot[]
}

export interface HyperparamDelta {
  component_id: string
  param: string
  old_value: number
  new_value: number
}

export interface ComponentDiff {
  component_id: string
  changed: boolean
  param_deltas: HyperparamDelta[]
  old_shapes: Record<string, string>
  new_shapes: Record<string, string>
  rationale: string
  invariants_held: string[]
  invariants_broken: string[]
}

export interface SchemaDiff {
  paper_id: string
  base_params: Record<string, number>
  modified_params: Record<string, number>
  component_diffs: ComponentDiff[]
  implementation_notes: string
}

export interface DiffResponse {
  baseline_trace: TraversalTrace
  modified_trace: TraversalTrace
  schema_diff: SchemaDiff
}
