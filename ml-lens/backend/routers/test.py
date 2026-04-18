from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/diff-demo", response_class=HTMLResponse)
async def diff_demo():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Diff Pipeline Test</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #FAFAFA;
                color: #1A1A1A;
                padding: 24px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 { font-size: 32px; margin-bottom: 8px; }
            .subtitle { color: #6B6B6B; margin-bottom: 24px; }

            .controls {
                background: white;
                border: 1px solid #E5E5E5;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 24px;
            }
            .control-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 12px;
                font-weight: 500;
            }
            input[type="range"] {
                width: 100%;
                height: 6px;
                border-radius: 3px;
                background: #E5E5E5;
                outline: none;
                -webkit-appearance: none;
            }
            input[type="range"]::-webkit-slider-thumb {
                -webkit-appearance: none;
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #0D9488;
                cursor: pointer;
            }
            input[type="range"]::-moz-range-thumb {
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #0D9488;
                cursor: pointer;
                border: none;
            }
            .value-display {
                display: inline-block;
                margin-left: 16px;
                font-weight: 600;
                color: #0D9488;
            }

            button {
                background: #0D9488;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.15s ease;
            }
            button:hover:not(:disabled) {
                background: #0F766E;
                transform: translateY(-1px);
            }
            button:disabled {
                background: #9CA3AF;
                cursor: not-allowed;
            }

            .results {
                background: white;
                border: 1px solid #E5E5E5;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 24px;
                display: none;
            }
            .results.show { display: block; }

            .error {
                background: #FEE2E2;
                color: #DC2626;
                padding: 12px 16px;
                border-radius: 6px;
                margin-bottom: 20px;
                display: none;
            }
            .error.show { display: block; }

            .loading {
                text-align: center;
                padding: 24px;
                color: #6B6B6B;
                display: none;
            }
            .loading.show { display: block; }
            .spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #E5E5E5;
                border-top-color: #0D9488;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }
            @keyframes spin { to { transform: rotate(360deg); } }

            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }
            .stat-card {
                background: #F9FAFB;
                border: 1px solid #E5E5E5;
                border-radius: 6px;
                padding: 16px;
            }
            .stat-label { font-size: 12px; color: #6B6B6B; text-transform: uppercase; }
            .stat-value { font-size: 24px; font-weight: 600; color: #0D9488; }

            .section {
                margin-bottom: 24px;
            }
            .section h3 {
                font-size: 18px;
                margin-bottom: 12px;
                font-weight: 600;
            }

            .component-cards {
                display: grid;
                gap: 12px;
            }
            .component-card {
                border-left: 3px solid #10B981;
                padding: 12px;
                background: #F9FAFB;
                border-radius: 4px;
            }
            .component-card.changed {
                border-left-color: #854F0B;
                background: #FAEEDA;
            }
            .component-name { font-weight: 600; }
            .component-detail { font-size: 0.9em; color: #6B6B6B; margin-top: 4px; }
            .component-rationale { font-size: 0.9em; margin-top: 8px; line-height: 1.4; }

            .implementation-notes {
                background: #F5F5F5;
                padding: 16px;
                border-radius: 6px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 13px;
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.5;
                overflow-x: auto;
            }

            .copy-btn {
                background: #6B7280;
                padding: 8px 12px;
                font-size: 14px;
                margin-bottom: 12px;
            }
            .copy-btn:hover:not(:disabled) {
                background: #4B5563;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Sandbox-to-Coding-Agent Pipeline</h1>
            <p class="subtitle">Test the hyperparameter diff generation</p>

            <div class="controls">
                <div class="control-group">
                    <label>
                        num_heads (baseline: 8)
                        <span class="value-display" id="numHeadsValue">8</span>
                    </label>
                    <input type="range" id="numHeadsSlider" min="1" max="16" step="1" value="8">
                </div>
                <button id="runBtn" onclick="runDiff()">Run Diff</button>
            </div>

            <div class="error" id="error"></div>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p style="margin-top: 12px;">Computing diff...</p>
            </div>

            <div class="results" id="results">
                <div class="section">
                    <h3>Parameters Changed</h3>
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-label">num_heads</div>
                            <div class="stat-value"><span id="baseNumHeads">8</span> → <span id="modNumHeads">8</span></div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">d_k</div>
                            <div class="stat-value"><span id="baseDk">64</span> → <span id="modDk">64</span></div>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h3>Component Impact</h3>
                    <div class="component-cards" id="componentCards"></div>
                </div>

                <div class="section">
                    <h3>Implementation Notes</h3>
                    <button class="copy-btn" onclick="copyNotes()">Copy to Clipboard</button>
                    <div class="implementation-notes" id="implNotes"></div>
                </div>
            </div>
        </div>

        <script>
            const numHeadsSlider = document.getElementById('numHeadsSlider');
            const numHeadsValue = document.getElementById('numHeadsValue');

            numHeadsSlider.addEventListener('input', (e) => {
                numHeadsValue.textContent = e.target.value;
            });

            async function runDiff() {
                const numHeads = parseInt(numHeadsSlider.value);
                const runBtn = document.getElementById('runBtn');
                const results = document.getElementById('results');
                const error = document.getElementById('error');
                const loading = document.getElementById('loading');

                error.classList.remove('show');
                results.classList.remove('show');
                loading.classList.add('show');
                runBtn.disabled = true;

                try {
                    const response = await fetch('/diff/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            manifest: {
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
                            },
                            base_params: { d_model: 512, num_heads: 8, d_ff: 2048, seq_len: 8 },
                            deltas: [{ component_id: "attention", param: "num_heads", old_value: 8, new_value: numHeads }]
                        })
                    });

                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.detail || `HTTP ${response.status}`);
                    }

                    const data = await response.json();
                    displayResults(data);
                } catch (err) {
                    error.textContent = 'Error: ' + err.message;
                    error.classList.add('show');
                } finally {
                    loading.classList.remove('show');
                    runBtn.disabled = false;
                }
            }

            function displayResults(data) {
                const diff = data.schema_diff;
                const baseParams = diff.base_params;
                const modParams = diff.modified_params;

                // Update stats
                document.getElementById('baseNumHeads').textContent = baseParams.num_heads;
                document.getElementById('modNumHeads').textContent = modParams.num_heads;
                document.getElementById('baseDk').textContent = Math.round(baseParams.d_model / baseParams.num_heads);
                document.getElementById('modDk').textContent = Math.round(modParams.d_model / modParams.num_heads);

                // Component cards
                const cardsHtml = diff.component_diffs.map(comp => `
                    <div class="component-card ${comp.changed ? 'changed' : ''}">
                        <div class="component-name">
                            ${comp.component_id}
                            ${comp.changed ? '<span style="color: #DC2626; margin-left: 8px;">(changed)</span>' : ''}
                        </div>
                        ${comp.changed ? `
                            <div class="component-detail">
                                ${comp.old_shapes.input} → ${comp.new_shapes.input}
                            </div>
                            <div class="component-rationale">${comp.rationale}</div>
                            ${comp.invariants_broken.length > 0 ? `
                                <div style="color: #DC2626; margin-top: 8px; font-size: 0.85em;">
                                    Broken: ${comp.invariants_broken.join(', ')}
                                </div>
                            ` : `
                                <div style="color: #10B981; margin-top: 8px; font-size: 0.85em;">
                                    ✓ No invariants broken
                                </div>
                            `}
                        ` : ''}
                    </div>
                `).join('');
                document.getElementById('componentCards').innerHTML = cardsHtml;

                // Implementation notes
                document.getElementById('implNotes').textContent = diff.implementation_notes;

                document.getElementById('results').classList.add('show');
            }

            function copyNotes() {
                const text = document.getElementById('implNotes').textContent;
                navigator.clipboard.writeText(text).then(() => {
                    alert('Copied to clipboard!');
                });
            }
        </script>
    </body>
    </html>
    """
