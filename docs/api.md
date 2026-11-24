# API quick reference

Base path: `/api`. Authenticate with `Authorization: Bearer <access_token>`.

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | /health | Public | Health check |
| POST | /auth/register | Public | Register donor |
| POST | /auth/login | Public | Login |
| GET | /auth/me | Authenticated | Current user |
| GET | /ashramas | Authenticated | Verified ashrama directory |
| POST | /donations | Donor | Submit donation |
| GET | /donations/mine | Donor | Donor history |
| GET | /admin/dashboard | Admin | Dashboard counts |
| GET | /admin/donations | Admin | All donations |
| GET | /admin/donors | Admin | Donor directory |
| GET | /admin/ashramas | Admin | All ashramas |
| POST | /admin/ashramas | Admin | Add ashrama |
| PATCH | /admin/ashramas/{id}/verification | Admin | Verify/unverify ashrama |
| PATCH | /admin/donations/{id}/status | Admin | Update donation status |

Interactive OpenAPI docs: `/docs`.
