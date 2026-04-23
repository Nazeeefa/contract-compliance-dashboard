# contract-compliance-dashboard

POC AI contract compliance dashboard with:
- Frontend: React + TypeScript + Tailwind
- Backend: FastAPI

## Run backend

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Test

```bash
cd backend
pytest -q
```
