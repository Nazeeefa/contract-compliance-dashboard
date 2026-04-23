# contract-compliance-dashboard

POC AI contract compliance dashboard with:
- Frontend: React + TypeScript + Tailwind
- Backend: FastAPI

## Run backend

```bash
cd /home/runner/work/contract-compliance-dashboard/contract-compliance-dashboard/backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run frontend

```bash
cd /home/runner/work/contract-compliance-dashboard/contract-compliance-dashboard/frontend
npm install
npm run dev
```

## Test

```bash
cd /home/runner/work/contract-compliance-dashboard/contract-compliance-dashboard/backend
pytest -q
```
