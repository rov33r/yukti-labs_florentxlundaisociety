# ML Lens

A collaborative ML evaluation and testing platform built with FastAPI, React, and DeepEval.

## Project Structure

```
ml-lens/
├── backend/          # FastAPI + Python backend
├── frontend/         # React + Vite frontend
├── evals/           # DeepEval + pytest evaluation suite
└── shared/          # Shared schema types (JSON)
```

## Quick Start

### Prerequisites
- Python 3.10+ (required)
- Node.js 18+ (required)
- API Keys: ANTHROPIC_API_KEY, E2B_API_KEY, LANGFUSE_KEY (optional for now)

### Running Locally (2 Terminals)

**Terminal 1 — Backend Server:**
```bash
cd ml-lens/backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```
Backend runs on: http://localhost:8000

**Terminal 2 — Frontend Server:**
```bash
cd ml-lens/frontend
npm install
npm run dev
```
Frontend runs on: http://localhost:5173

Visit http://localhost:5173 to see the dashboard!

### Using Docker Compose (Optional)
```bash
cp .env.example .env
docker-compose up
```
- Backend: http://localhost:8000
- E2B Sandbox: http://localhost:4242

## Development Workflow

### Creating a Feature
1. Create branch: `git checkout -b feature/your-feature`
2. Make changes & test locally
3. Push & create PR for review: `git push origin feature/your-feature`
4. Review together, then merge to main

### Running Tests
```bash
cd ml-lens/evals
pip install -r requirements.txt
pytest
```

## Tech Stack
- **Backend**: FastAPI, Python
- **Frontend**: React, Vite
- **Testing**: DeepEval, pytest
- **Sandbox**: E2B
- **LLM**: Anthropic Claude API
- **Observability**: Langfuse

