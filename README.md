# FoodBridge

FoodBridge connects food donors with ashramas and community-care organizations in Karnataka. This MVP implements **Admin + Donor** workflows first; delivery-partner pickup and ashrama receipt confirmation are planned next.

## MVP features
- Donor registration and JWT login.
- Donor dashboard with a Karnataka ashrama directory.
- Donation submission (food, quantity, preparation time, safe-consumption deadline, allergens, pickup address and notes).
- Donor donation history and status tracking.
- Admin dashboard with donor/ashrama/donation counts.
- Admin review of donations, status updates, ashrama creation and verification.
- Audit timeline for donation status changes.
- Demo seed data clearly labelled as examples, not verified partner organizations.

## Stack
- React + Vite
- Python FastAPI + SQLAlchemy
- SQLite by default; PostgreSQL supported through `DATABASE_URL`
- JWT authentication and role-based authorization
- Docker Compose

## Run locally

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
API: http://localhost:8000  
Swagger: http://localhost:8000/docs

On first startup, the API creates tables, a configurable admin account, and clearly marked demo ashramas. Change the default admin password immediately.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The Vite dev server proxies `/api` to the backend.

### Docker Compose
```bash
cp backend/.env.example .env
# Edit ADMIN_PASSWORD and SECRET_KEY before exposing the app.
docker compose up --build
```
Open http://localhost:8080.

## Default local admin
Configured with `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the environment. Defaults are for local development only: `admin@foodbridge.local` / `ChangeMe123!`. Never deploy with these defaults.

## Donation lifecycle
`submitted → approved → assigned → picked_up → in_transit → delivered → confirmed`
Admin may also set `rejected` or `cancelled`. Current MVP allows Admin to update statuses. Delivery partner actions and Ashrama confirmation will be implemented in the next phase.

## Food safety
The app captures preparation time, safe-consumption deadline and allergen notes. It does not certify food safety. Admins and receiving organizations must assess packaging, temperature control, transport time, dietary restrictions and local food-safety requirements before accepting a donation. Do not submit food that is spoiled, contaminated or outside its safe-consumption window.

## Demo ashramas
Seed records are illustrative demo data in Bengaluru, Mysuru, Hubballi and Mangaluru. They are not endorsements or confirmed partners. Replace them with organizations whose identity, address, contact, capacity and willingness to receive donations have been independently verified. The admin can add and verify real organizations.

## API overview
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/ashramas` (authenticated), `POST /api/admin/ashramas`
- `POST /api/donations`, `GET /api/donations/mine`
- `GET /api/admin/dashboard`, `GET /api/admin/donations`, `PATCH /api/admin/donations/{id}/status`
- `GET /api/health`

Full interactive API documentation is available at `/docs`.

## Security notes
- Use a long random `SECRET_KEY` and strong admin password.
- Set `COOKIE_SECURE`/HTTPS appropriately when deploying; tokens are currently returned to the frontend and held in session storage.
- Restrict CORS, add rate limiting, email/phone verification and backups before production.
- Do not store payment-card data or unnecessary personal information.
