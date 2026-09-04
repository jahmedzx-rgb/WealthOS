# WealthOS

The official WealthOS development source is this repository under the Codex workspace.

## Local services

- Frontend: `http://localhost:5173`
- API: `http://127.0.0.1:8001`
- PostgreSQL database: configured through `DATABASE_URL`

## Backend setup

1. Create a Python virtual environment.
2. Install `requirements/dev.txt`.
3. Copy `.env.example` to `.env` and set local credentials.
4. Run `alembic upgrade head`.
5. Start `uvicorn main:app --host 127.0.0.1 --port 8001`.

## Frontend setup

1. Enter the `frontend` directory.
2. Run `npm install`.
3. Optionally copy `.env.example` to `.env` to override the API URL.
4. Run `npm run dev`.

Imported financial documents are analyzed locally in the browser. Extracted operations remain drafts in the Review Queue until the user confirms or ignores them.
