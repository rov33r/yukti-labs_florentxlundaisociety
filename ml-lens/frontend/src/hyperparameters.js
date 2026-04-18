export const PARAM_DEFAULTS = {
  '1': { max_seq_len: 512 },
  '2': { d_model: 512, vocab_size: 50000 },
  '3': { max_seq_len: 512, dropout: 0.1 },
  '4': { num_layers: 6, dropout: 0.1 },
  '5': { num_heads: 8, d_model: 512, dropout: 0.1 },
  '6': { d_ff: 2048, dropout: 0.1, activation: 'relu' },
  '7': { num_layers: 6, dropout: 0.1 },
  '8': { num_heads: 8, d_model: 512, dropout: 0.1 },
  '9': { num_heads: 8, d_model: 512, dropout: 0.1 },
  '10': { vocab_size: 50000, temperature: 1.0 },
}

// Schema for each param: label, type, min, max, step, unit, options (for select)
// max is only set where there is a real mathematical constraint.
// Architectural params (d_model, d_ff, num_heads, etc.) have no hard ceiling.
export const PARAM_META = {
  '1': [
    { key: 'max_seq_len', label: 'Max sequence length', type: 'number', min: 1,    step: 64,   unit: 'tokens' },
  ],
  '2': [
    { key: 'd_model',    label: 'Model dimension', type: 'number', min: 1,    step: 64,   unit: 'dims' },
    { key: 'vocab_size', label: 'Vocabulary size', type: 'number', min: 1,    step: 1000, unit: 'tokens' },
  ],
  '3': [
    { key: 'max_seq_len', label: 'Max sequence length', type: 'number', min: 1,    step: 64,   unit: 'tokens' },
    { key: 'dropout',     label: 'Dropout',             type: 'float',  min: 0,    max: 1,     step: 0.05 },
  ],
  '4': [
    { key: 'num_layers', label: 'Number of layers', type: 'number', min: 1, step: 1, unit: 'layers' },
    { key: 'dropout',    label: 'Dropout',           type: 'float',  min: 0, max: 1, step: 0.05 },
  ],
  '5': [
    { key: 'num_heads', label: 'Attention heads', type: 'number', min: 1, step: 1,  unit: 'heads' },
    { key: 'd_model',   label: 'Model dimension', type: 'number', min: 1, step: 64, unit: 'dims' },
    { key: 'dropout',   label: 'Dropout',          type: 'float',  min: 0, max: 1,  step: 0.05 },
  ],
  '6': [
    { key: 'd_ff',       label: 'FFN hidden size', type: 'number', min: 1,    step: 256, unit: 'dims' },
    { key: 'dropout',    label: 'Dropout',          type: 'float',  min: 0,    max: 1,    step: 0.05 },
    { key: 'activation', label: 'Activation',       type: 'select', options: ['relu', 'gelu', 'swish'] },
  ],
  '7': [
    { key: 'num_layers', label: 'Number of layers', type: 'number', min: 1, step: 1, unit: 'layers' },
    { key: 'dropout',    label: 'Dropout',           type: 'float',  min: 0, max: 1, step: 0.05 },
  ],
  '8': [
    { key: 'num_heads', label: 'Attention heads', type: 'number', min: 1, step: 1,  unit: 'heads' },
    { key: 'd_model',   label: 'Model dimension', type: 'number', min: 1, step: 64, unit: 'dims' },
    { key: 'dropout',   label: 'Dropout',          type: 'float',  min: 0, max: 1,  step: 0.05 },
  ],
  '9': [
    { key: 'num_heads', label: 'Attention heads', type: 'number', min: 1, step: 1,  unit: 'heads' },
    { key: 'd_model',   label: 'Model dimension', type: 'number', min: 1, step: 64, unit: 'dims' },
    { key: 'dropout',   label: 'Dropout',          type: 'float',  min: 0, max: 1,  step: 0.05 },
  ],
  '10': [
    { key: 'vocab_size',  label: 'Vocabulary size', type: 'number', min: 1,    step: 1000, unit: 'tokens' },
    { key: 'temperature', label: 'Temperature',      type: 'float',  min: 0.01, max: 10,    step: 0.05 },
  ],
}

export function isModified(nodeId, params) {
  const defaults = PARAM_DEFAULTS[nodeId]
  if (!defaults || !params) return false
  return Object.keys(defaults).some((k) => params[k] !== defaults[k])
}

export function getValidationWarnings(nodeId, params) {
  const warnings = []
  if (!params) return warnings

  const { num_heads, d_model, dropout, temperature } = params

  if (num_heads !== undefined && d_model !== undefined && d_model % num_heads !== 0) {
    warnings.push(`d_model (${d_model}) must be divisible by num_heads (${num_heads})`)
  }
  if (dropout !== undefined && (dropout < 0 || dropout > 1)) {
    warnings.push('Dropout must be between 0 and 1')
  }
  if (temperature !== undefined && temperature <= 0) {
    warnings.push('Temperature must be greater than 0')
  }

  return warnings
}
