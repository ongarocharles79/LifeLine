# LIFELINE — Phase 1 Prototype

**Connecting Healthcare, Saving Lives Across Kisumu County**

LIFELINE is a healthcare operations platform prototype for coordinating patient
referrals, ambulance dispatch, ambulance tracking, and clinical handover
between healthcare facilities in Kisumu County, Kenya.

> **This is a Phase 1 demo/prototype.** All facility coordinates, ambulance
> positions, driver identities, and patient records are simulated demo data.
> Ambulance movement is a simulated straight-line interpolation, not real GPS
> tracking. See "What is deferred to Phase 2" below.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m streamlit run app.py
```

The first run seeds the SQLite database (`lifeline.db`) automatically with
demo facilities, ambulances, users, and ~30 days of historical activity.

## Demo login credentials

| Role              | Email                  | Password      |
|-------------------|-------------------------|---------------|
| Admin             | admin@demo.lifeline    | ChangeMe123!  |
| Hospital Staff    | staff@demo.lifeline    | ChangeMe123!  |
| Ambulance Driver  | driver@demo.lifeline   | ChangeMe123!  |
| System Manager    | manager@demo.lifeline  | ChangeMe123!  |

These are demo-only accounts using a simplified, non-production password
hashing scheme (see `services/auth_service.py`). Production authentication
(Argon2id/OIDC) is a later phase.

## Project structure

```
app.py                  Entry point: landing/login + authenticated navigation
config/settings.py      Central config: cost constants, demo accounts, colors
database/                SQLAlchemy engine/session, models, idempotent seeding
services/                Business logic (cost, ambulance, referral, tracking, auth)
components/              Reusable Streamlit UI pieces (cards, charts, maps, tables)
pages/                   One module per app page, each exposing render()
data/seed_data.py        Static demo data: hospitals, name/plate pools
tests/                   Pytest suite for service-layer logic
```

## What works in Phase 1

- Public landing page, demo login, role-aware navigation
- Dashboard with live KPIs and charts computed from the database
- Facility + ambulance fleet browsing on an interactive map
- Referral creation with Haversine-based distance/cost estimation
- Auto and manual ambulance assignment
- Active mission tracking with simulated step-by-step ambulance movement
- Clinical handover capture, completing the referral and freeing the ambulance
- Reports page with CSV export

## What is deferred to Phase 2+

Real GPS tracking, real road routing/ETA, Postgres, Redis, WebSockets,
Stripe/M-Pesa billing, real SMS/email notifications, production
authentication (Argon2id/OIDC), native mobile apps, and any real healthcare
system integrations.
