# pathwiseaiUIgapfix.md
## PathWise AI — Multi-Tenant UI & User Experience Complete Implementation Spec
### For Claude CLI (Claude Code) — Execute fully, autonomously, in order

**Project:** PathWise AI — Team Pathfinders, COSC6370-001  
**Purpose:** Transform PathWise AI into a production-grade, multi-tenant SaaS platform with role-separated dashboards, 8 SME business owner user accounts + 1 super-admin account, billing, ticketing, LSTM controls, and a professional modern UI  
**Stack:** React 18 + TypeScript + Tailwind CSS + shadcn/ui | FastAPI + Python | TimescaleDB | JWT Auth  
**UI Theme:** Dark sidebar + clean light content area (consistent with SDD §6 design philosophy)

---

## READ THIS FIRST — EXECUTION RULES

1. Work through every section in order. Do NOT skip sections.
2. Before writing any React component, read the existing `frontend/` directory structure.
3. Before writing any FastAPI route, check `server/` for existing routers to avoid conflicts.
4. Every new database table must be added to `server/db/migrations/` as a new Alembic migration.
5. Run `npm run build` after completing the frontend. Fix all TypeScript errors before moving on.
6. Run `pytest tests/ui/` after completing the backend. All tests must pass.
7. Seed data (all 9 accounts + subscriptions + tickets + billing) must be inserted by `scripts/seed_ui_data.py`.
8. The continuous data simulator must start automatically with `docker compose up`.

---

## SECTION 0 — DIRECTORY STRUCTURE TO CREATE

Create the following new directories if they do not exist:

```
frontend/src/
  pages/
    auth/           # Login page (shared)
    admin/          # All admin-only pages
    user/           # All user-only pages
    shared/         # Components used by both
  components/
    layout/         # AdminLayout, UserLayout, Sidebar, Topbar
    charts/         # Recharts wrappers
    ui/             # shadcn/ui re-exports + custom atoms
  hooks/            # useAuth, useWebSocket, useSiteData
  context/          # AuthContext, ThemeContext
  types/            # TypeScript interfaces for all entities
  utils/            # formatters, constants, api client

server/
  routers/
    admin.py        # Admin-only endpoints
    users.py        # User management (admin)
    billing.py      # Billing + subscription endpoints
    tickets.py      # Support ticket endpoints
    profile.py      # User profile endpoints
    lstm_control.py # LSTM model control (admin-only)
    simulator.py    # Continuous data simulator control

scripts/
  seed_ui_data.py           # Insert all 9 accounts + demo data
  continuous_simulator.py   # Per-user background data generator

tests/
  ui/
    test_auth_roles.py
    test_billing_api.py
    test_tickets_api.py
    test_admin_api.py
    test_user_api.py
    test_continuous_data.py
```

---

## SECTION 1 — ACCOUNT SEED DATA (9 ACCOUNTS)

### 1.1 — Create `scripts/seed_ui_data.py`

This script inserts all accounts, subscriptions, sites, and sample data into TimescaleDB. Run it once on first boot: `python scripts/seed_ui_data.py`

```python
"""
PathWise AI — UI Seed Data Script
Inserts 1 admin + 8 SME business owner user accounts with realistic demo data.
Run: python scripts/seed_ui_data.py
"""

import os, sys, bcrypt, json, random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql://pathwise:pathwise@localhost:5432/pathwise")
engine = create_engine(DB_URL)

# ─── Account definitions ─────────────────────────────────────────────────────

ADMIN_ACCOUNT = {
    "id": "admin-001",
    "name": "Vineeth Reddy (Super Admin)",
    "email": "admin@pathwise.ai",
    "password": "Admin@PathWise2026",
    "role": "SUPER_ADMIN",
    "company": "PathWise AI",
    "avatar_initials": "VA",
    "plan": None
}

USER_ACCOUNTS = [
    {
        "id": "user-001",
        "name": "Marcus Rivera",
        "email": "marcus@riveralogistics.com",
        "password": "Rivera@2026",
        "role": "BUSINESS_OWNER",
        "company": "Rivera Logistics LLC",
        "industry": "Logistics",
        "sites": ["Dallas HQ", "Houston Depot"],
        "plan": "professional",
        "mrr": 149.00,
        "avatar_initials": "MR"
    },
    {
        "id": "user-002",
        "name": "Priya Nair",
        "email": "priya@nairmedical.com",
        "password": "NairMed@2026",
        "role": "BUSINESS_OWNER",
        "company": "Nair Medical Group",
        "industry": "Healthcare",
        "sites": ["Main Clinic", "Lab Annex", "Pharmacy"],
        "plan": "enterprise",
        "mrr": 299.00,
        "avatar_initials": "PN"
    },
    {
        "id": "user-003",
        "name": "DeShawn Carter",
        "email": "deshawn@carterretail.com",
        "password": "Carter@2026",
        "role": "BUSINESS_OWNER",
        "company": "Carter Retail Group",
        "industry": "Retail",
        "sites": ["Store A", "Store B", "Warehouse"],
        "plan": "starter",
        "mrr": 49.00,
        "avatar_initials": "DC"
    },
    {
        "id": "user-004",
        "name": "Sofia Morales",
        "email": "sofia@moralesacademy.edu",
        "password": "Sofia@2026",
        "role": "BUSINESS_OWNER",
        "company": "Morales Academy",
        "industry": "Education",
        "sites": ["Main Campus", "Sports Complex"],
        "plan": "professional",
        "mrr": 149.00,
        "avatar_initials": "SM"
    },
    {
        "id": "user-005",
        "name": "Kenji Tanaka",
        "email": "kenji@tanakafab.com",
        "password": "Tanaka@2026",
        "role": "BUSINESS_OWNER",
        "company": "Tanaka Fabrications",
        "industry": "Manufacturing",
        "sites": ["Factory Floor", "Office Block"],
        "plan": "professional",
        "mrr": 149.00,
        "avatar_initials": "KT"
    },
    {
        "id": "user-006",
        "name": "Amara Osei",
        "email": "amara@oseifinance.com",
        "password": "Amara@2026",
        "role": "BUSINESS_OWNER",
        "company": "Osei Financial Services",
        "industry": "Finance",
        "sites": ["Main Office", "Branch East"],
        "plan": "enterprise",
        "mrr": 299.00,
        "avatar_initials": "AO"
    },
    {
        "id": "user-007",
        "name": "Elena Petrov",
        "email": "elena@petrovhotel.com",
        "password": "Elena@2026",
        "role": "BUSINESS_OWNER",
        "company": "Petrov Hospitality Group",
        "industry": "Hospitality",
        "sites": ["Downtown Hotel", "Airport Hotel"],
        "plan": "starter",
        "mrr": 49.00,
        "avatar_initials": "EP"
    },
    {
        "id": "user-008",
        "name": "Tobias Bauer",
        "email": "tobias@bauertech.io",
        "password": "Bauer@2026",
        "role": "BUSINESS_OWNER",
        "company": "Bauer Tech Solutions",
        "industry": "Technology",
        "sites": ["Dev Office", "Server Room"],
        "plan": "enterprise",
        "mrr": 299.00,
        "avatar_initials": "TB"
    }
]

PLANS = {
    "starter":      {"name": "Starter",      "price": 49.00,  "sites": 2,  "links_per_site": 2, "features": ["basic_dashboard","email_alerts","csv_export"]},
    "professional": {"name": "Professional", "price": 149.00, "sites": 5,  "links_per_site": 4, "features": ["full_dashboard","lstm_forecasting","ibn","sandbox","pdf_export","priority_support"]},
    "enterprise":   {"name": "Enterprise",   "price": 299.00, "sites": 20, "links_per_site": 6, "features": ["full_dashboard","lstm_forecasting","ibn","sandbox","pdf_export","dedicated_support","hipaa_audit","multi_site_analytics"]},
}

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()

def seed():
    with engine.connect() as conn:
        # Create tables if they don't exist
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS app_users (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            email VARCHAR UNIQUE NOT NULL,
            password_hash VARCHAR NOT NULL,
            role VARCHAR NOT NULL DEFAULT 'BUSINESS_OWNER',
            company VARCHAR,
            industry VARCHAR,
            avatar_initials VARCHAR(3),
            is_active BOOLEAN DEFAULT TRUE,
            failed_attempts INT DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR REFERENCES app_users(id),
            plan_id VARCHAR NOT NULL,
            plan_name VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'active',
            monthly_price NUMERIC(10,2),
            billing_cycle VARCHAR DEFAULT 'monthly',
            start_date DATE DEFAULT CURRENT_DATE,
            next_billing_date DATE,
            payment_method VARCHAR DEFAULT 'card_ending_4242',
            card_last4 VARCHAR(4) DEFAULT '4242',
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS sites (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR REFERENCES app_users(id),
            name VARCHAR NOT NULL,
            location VARCHAR,
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS support_tickets (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR REFERENCES app_users(id),
            subject VARCHAR NOT NULL,
            description TEXT,
            priority VARCHAR DEFAULT 'medium',
            status VARCHAR DEFAULT 'open',
            category VARCHAR DEFAULT 'general',
            admin_response TEXT,
            resolved_by VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR REFERENCES app_users(id),
            subscription_id VARCHAR,
            amount NUMERIC(10,2),
            status VARCHAR DEFAULT 'paid',
            period_start DATE,
            period_end DATE,
            issued_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS lstm_model_configs (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT,
            sequence_length INT DEFAULT 60,
            hidden_units INT DEFAULT 128,
            num_layers INT DEFAULT 2,
            dropout NUMERIC(4,3) DEFAULT 0.2,
            learning_rate NUMERIC(8,6) DEFAULT 0.001,
            batch_size INT DEFAULT 32,
            epochs INT DEFAULT 100,
            is_active BOOLEAN DEFAULT FALSE,
            accuracy NUMERIC(5,2),
            mae_latency NUMERIC(6,2),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """))

        # Insert admin
        all_accounts = [ADMIN_ACCOUNT] + USER_ACCOUNTS
        for acc in all_accounts:
            conn.execute(text("""
            INSERT INTO app_users (id, name, email, password_hash, role, company, industry, avatar_initials)
            VALUES (:id, :name, :email, :ph, :role, :company, :industry, :ai)
            ON CONFLICT (email) DO NOTHING
            """), {"id": acc["id"], "name": acc["name"], "email": acc["email"],
                   "ph": hash_password(acc["password"]), "role": acc["role"],
                   "company": acc.get("company"), "industry": acc.get("industry"),
                   "ai": acc.get("avatar_initials", acc["name"][:2].upper())})

        # Insert subscriptions and sites for each user
        import uuid
        for acc in USER_ACCOUNTS:
            plan = acc["plan"]
            plan_meta = PLANS[plan]
            sub_id = f"sub-{acc['id']}"
            conn.execute(text("""
            INSERT INTO subscriptions (id, user_id, plan_id, plan_name, monthly_price, next_billing_date)
            VALUES (:id, :uid, :pid, :pname, :price, :nbd)
            ON CONFLICT DO NOTHING
            """), {"id": sub_id, "uid": acc["id"], "pid": plan, "pname": plan_meta["name"],
                   "price": plan_meta["price"],
                   "nbd": (datetime.now() + timedelta(days=30)).date()})

            for i, site_name in enumerate(acc["sites"]):
                site_id = f"site-{acc['id']}-{i+1}"
                conn.execute(text("""
                INSERT INTO sites (id, user_id, name, location)
                VALUES (:id, :uid, :name, :loc)
                ON CONFLICT DO NOTHING
                """), {"id": site_id, "uid": acc["id"], "name": site_name,
                       "loc": f"{acc['company']} — {site_name}"})

            # Generate 3 invoices per user
            for m in range(3):
                inv_id = f"inv-{acc['id']}-{m+1}"
                period_start = datetime.now().date() - timedelta(days=30*(m+1))
                period_end   = datetime.now().date() - timedelta(days=30*m)
                conn.execute(text("""
                INSERT INTO invoices (id, user_id, subscription_id, amount, period_start, period_end)
                VALUES (:id, :uid, :sid, :amt, :ps, :pe) ON CONFLICT DO NOTHING
                """), {"id": inv_id, "uid": acc["id"], "sid": sub_id,
                       "amt": plan_meta["price"], "ps": period_start, "pe": period_end})

        # Insert sample tickets
        sample_tickets = [
            ("ticket-001", "user-001", "Fiber link showing false degradation alerts",
             "Getting alerts every 5 minutes but link is healthy", "high", "bug"),
            ("ticket-002", "user-003", "How to export telemetry as CSV?",
             "Cannot find the export button on dashboard", "low", "how_to"),
            ("ticket-004", "user-002", "HIPAA audit log export format",
             "Need the audit log in a specific format for compliance", "medium", "compliance"),
            ("ticket-005", "user-006", "Upgrade plan from Enterprise to custom",
             "We need more than 20 sites", "medium", "billing"),
        ]
        for t in sample_tickets:
            conn.execute(text("""
            INSERT INTO support_tickets (id, user_id, subject, description, priority, category)
            VALUES (:id, :uid, :sub, :desc, :pri, :cat) ON CONFLICT DO NOTHING
            """), {"id": t[0], "uid": t[1], "sub": t[2], "desc": t[3], "pri": t[4], "cat": t[5]})

        # Insert LSTM model configs
        lstm_models = [
            ("lstm-v1", "LSTM v1 — Baseline", "Original production model", 60, 64, 2, 0.2, 0.001, 32, 100, True, 90.5, 6.94),
            ("lstm-v2", "LSTM v2 — Deep", "Deeper architecture with 4 layers", 90, 128, 4, 0.3, 0.0005, 64, 150, False, 92.1, 5.41),
            ("lstm-v3", "LSTM v3 — Experimental", "Bidirectional LSTM experiment", 60, 256, 2, 0.25, 0.001, 32, 200, False, None, None),
        ]
        for m in lstm_models:
            conn.execute(text("""
            INSERT INTO lstm_model_configs (id,name,description,sequence_length,hidden_units,num_layers,
                dropout,learning_rate,batch_size,epochs,is_active,accuracy,mae_latency)
            VALUES (:id,:name,:desc,:sl,:hu,:nl,:do,:lr,:bs,:ep,:ia,:acc,:mae)
            ON CONFLICT DO NOTHING
            """), {"id": m[0],"name": m[1],"desc": m[2],"sl": m[3],"hu": m[4],"nl": m[5],
                   "do": m[6],"lr": m[7],"bs": m[8],"ep": m[9],"ia": m[10],"acc": m[11],"mae": m[12]})

        conn.commit()
        print("✓ Seed data inserted successfully.")
        print("\nLogin credentials:")
        print(f"  Admin:   admin@pathwise.ai         / Admin@PathWise2026")
        for u in USER_ACCOUNTS:
            print(f"  User:    {u['email']:<35} / {u['password']}")

if __name__ == "__main__":
    seed()
```

---

## SECTION 2 — CONTINUOUS DATA SIMULATOR

### 2.1 — Create `scripts/continuous_simulator.py`

This script runs as a background process and generates realistic telemetry data for all 8 user accounts continuously so the admin can see live data for every user.

```python
"""
PathWise AI — Continuous Per-User Data Simulator
Generates realistic WAN telemetry for all 8 user sites at 1 Hz.
Start: python scripts/continuous_simulator.py
Auto-started by docker-compose via the 'simulator' service.
"""

import asyncio, random, time, json, os
from datetime import datetime
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql://pathwise:pathwise@localhost:5432/pathwise")
engine = create_engine(DB_URL)

# Site → link configuration
SITE_LINKS = {
    "site-user-001-1": ["fiber", "broadband"],
    "site-user-001-2": ["5g", "broadband"],
    "site-user-002-1": ["fiber", "satellite", "5g"],
    "site-user-002-2": ["fiber", "broadband"],
    "site-user-002-3": ["broadband", "5g"],
    "site-user-003-1": ["fiber", "broadband"],
    "site-user-003-2": ["broadband", "5g"],
    "site-user-003-3": ["fiber", "satellite"],
    "site-user-004-1": ["fiber", "broadband", "5g"],
    "site-user-004-2": ["broadband", "satellite"],
    "site-user-005-1": ["fiber", "broadband"],
    "site-user-005-2": ["fiber", "5g"],
    "site-user-006-1": ["fiber", "broadband", "satellite"],
    "site-user-006-2": ["fiber", "5g"],
    "site-user-007-1": ["broadband", "satellite"],
    "site-user-007-2": ["fiber", "broadband"],
    "site-user-008-1": ["fiber", "5g"],
    "site-user-008-2": ["fiber", "broadband"],
}

# Per-link baseline characteristics
LINK_BASELINES = {
    "fiber":     {"latency": 8,   "jitter": 1.2, "loss": 0.01, "bw": 1000},
    "broadband": {"latency": 22,  "jitter": 3.5, "loss": 0.05, "bw": 300},
    "satellite": {"latency": 590, "jitter": 40,  "loss": 0.3,  "bw": 50},
    "5g":        {"latency": 12,  "jitter": 2.0, "loss": 0.02, "bw": 500},
}

def _gen_metric(base: float, noise_pct: float = 0.15,
                spike_chance: float = 0.03) -> float:
    val = base * (1 + random.uniform(-noise_pct, noise_pct))
    if random.random() < spike_chance:
        val *= random.uniform(1.5, 4.0)  # simulate brownout spike
    return round(max(0, val), 3)

def _health_score(lat: float, jitter: float, loss: float,
                  base_lat: float) -> int:
    lat_penalty  = min(40, (lat / base_lat - 1) * 30) if lat > base_lat else 0
    jit_penalty  = min(20, jitter * 2)
    loss_penalty = min(40, loss * 200)
    return max(0, min(100, round(100 - lat_penalty - jit_penalty - loss_penalty)))

async def simulate_site(site_id: str, links: list):
    with engine.connect() as conn:
        while True:
            for link_type in links:
                b = LINK_BASELINES[link_type]
                lat   = _gen_metric(b["latency"])
                jit   = _gen_metric(b["jitter"])
                loss  = _gen_metric(b["loss"])
                score = _health_score(lat, jit, loss, b["latency"])
                ts    = datetime.utcnow()

                conn.execute(text("""
                INSERT INTO telemetry_live
                    (site_id, link_type, latency_ms, jitter_ms, packet_loss_pct,
                     health_score, bandwidth_mbps, timestamp)
                VALUES
                    (:sid, :lt, :lat, :jit, :loss, :score, :bw, :ts)
                """), {
                    "sid": site_id, "lt": link_type,
                    "lat": lat, "jit": jit, "loss": loss,
                    "score": score, "bw": b["bw"] * random.uniform(0.6, 1.0),
                    "ts": ts
                })
            conn.commit()
            await asyncio.sleep(1)

async def main():
    # Ensure telemetry_live hypertable exists
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS telemetry_live (
            id BIGSERIAL,
            site_id VARCHAR,
            link_type VARCHAR,
            latency_ms NUMERIC(10,3),
            jitter_ms NUMERIC(10,3),
            packet_loss_pct NUMERIC(8,4),
            health_score INT,
            bandwidth_mbps NUMERIC(10,2),
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        SELECT create_hypertable('telemetry_live','timestamp',if_not_exists=>TRUE);
        """))
        conn.commit()

    print(f"[Simulator] Starting continuous simulation for {len(SITE_LINKS)} sites...")
    tasks = [simulate_site(sid, links) for sid, links in SITE_LINKS.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

### 2.2 — Add simulator service to `docker-compose.yml`

```yaml
  simulator:
    build: .
    container_name: pathwise_simulator
    command: python scripts/continuous_simulator.py
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - pathwise_net
```

---

## SECTION 3 — BACKEND API ROUTES

### 3.1 — Extended JWT with role claim (`server/auth.py` — update)

Ensure the JWT payload includes `role` and `user_id`:

```python
def create_access_token(user_id: str, role: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=int(os.getenv("JWT_EXPIRY_MINUTES", "60")))
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")

def require_admin(token: str = Depends(oauth2_scheme)) -> dict:
    claims = verify_token(token)
    if claims["role"] != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims

def require_user(token: str = Depends(oauth2_scheme)) -> dict:
    claims = verify_token(token)
    if claims["role"] not in ("BUSINESS_OWNER", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="User access required")
    return claims
```

### 3.2 — Auth routes (`server/routers/auth.py` — update login)

```python
@router.post("/api/v1/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT * FROM app_users WHERE email = :e"), {"e": body.email}
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check lockout
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(status_code=423, detail="Account locked. Contact admin.")

    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        attempts = user.failed_attempts + 1
        locked = datetime.utcnow() + timedelta(minutes=30) if attempts >= 5 else None
        db.execute(text("UPDATE app_users SET failed_attempts=:a, locked_until=:l WHERE id=:id"),
                   {"a": attempts, "l": locked, "id": user.id})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Reset on success
    db.execute(text("UPDATE app_users SET failed_attempts=0, locked_until=NULL WHERE id=:id"),
               {"id": user.id})
    db.commit()

    token = create_access_token(user.id, user.role, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "name": user.name,
        "company": user.company,
        "avatar_initials": user.avatar_initials,
        "redirect_to": "/admin/dashboard" if user.role == "SUPER_ADMIN" else "/user/dashboard"
    }
```

### 3.3 — Create `server/routers/billing.py`

```python
"""Billing and subscription management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from server.auth import require_user, require_admin
from server.db import get_db

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

PLANS = {
    "starter":      {"name": "Starter",      "price": 49.00,  "sites": 2,  "links": 2},
    "professional": {"name": "Professional", "price": 149.00, "sites": 5,  "links": 4},
    "enterprise":   {"name": "Enterprise",   "price": 299.00, "sites": 20, "links": 6},
}

@router.get("/plans")
def list_plans():
    """Public — return all available subscription plans."""
    return {"plans": [{"id": k, **v} for k, v in PLANS.items()]}

@router.get("/subscription")
def get_my_subscription(claims=Depends(require_user), db=Depends(get_db)):
    row = db.execute(text("""
        SELECT s.*, u.name, u.email, u.company FROM subscriptions s
        JOIN app_users u ON u.id = s.user_id
        WHERE s.user_id = :uid
    """), {"uid": claims["sub"]}).fetchone()
    if not row:
        raise HTTPException(404, "No active subscription")
    return dict(row._mapping)

@router.post("/subscription/upgrade")
def upgrade_subscription(body: dict, claims=Depends(require_user), db=Depends(get_db)):
    """Change the user's plan (upgrade or downgrade)."""
    new_plan = body.get("plan_id")
    if new_plan not in PLANS:
        raise HTTPException(400, f"Unknown plan: {new_plan}")
    meta = PLANS[new_plan]
    db.execute(text("""
        UPDATE subscriptions SET plan_id=:pid, plan_name=:pname, monthly_price=:price,
        next_billing_date = CURRENT_DATE + INTERVAL '30 days'
        WHERE user_id=:uid
    """), {"pid": new_plan, "pname": meta["name"], "price": meta["price"], "uid": claims["sub"]})
    db.commit()
    return {"success": True, "plan": meta}

@router.post("/subscription/cancel")
def cancel_subscription(claims=Depends(require_user), db=Depends(get_db)):
    db.execute(text("UPDATE subscriptions SET status='cancelled' WHERE user_id=:uid"),
               {"uid": claims["sub"]})
    db.commit()
    return {"success": True, "status": "cancelled"}

@router.get("/invoices")
def get_invoices(claims=Depends(require_user), db=Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM invoices WHERE user_id=:uid ORDER BY issued_at DESC
    """), {"uid": claims["sub"]}).fetchall()
    return {"invoices": [dict(r._mapping) for r in rows]}

@router.get("/admin/revenue")
def admin_revenue_dashboard(claims=Depends(require_admin), db=Depends(get_db)):
    """Admin-only revenue summary."""
    total_mrr = db.execute(text("""
        SELECT COALESCE(SUM(monthly_price),0) as mrr FROM subscriptions WHERE status='active'
    """)).scalar()
    by_plan = db.execute(text("""
        SELECT plan_name, COUNT(*) as count, SUM(monthly_price) as revenue
        FROM subscriptions WHERE status='active'
        GROUP BY plan_name ORDER BY revenue DESC
    """)).fetchall()
    monthly = db.execute(text("""
        SELECT DATE_TRUNC('month', issued_at) as month,
               SUM(amount) as revenue, COUNT(*) as invoices
        FROM invoices WHERE status='paid'
        GROUP BY month ORDER BY month DESC LIMIT 12
    """)).fetchall()
    return {
        "total_mrr": float(total_mrr),
        "arr": float(total_mrr) * 12,
        "by_plan": [dict(r._mapping) for r in by_plan],
        "monthly_trend": [dict(r._mapping) for r in monthly]
    }
```

### 3.4 — Create `server/routers/tickets.py`

```python
"""Support ticket endpoints for users and admin."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
from server.auth import require_user, require_admin
from server.db import get_db
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets"])

class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"
    category: str = "general"

class TicketResponse(BaseModel):
    admin_response: str
    status: str = "resolved"

@router.post("/")
def raise_ticket(body: TicketCreate, claims=Depends(require_user), db=Depends(get_db)):
    tid = f"ticket-{uuid.uuid4().hex[:8]}"
    db.execute(text("""
        INSERT INTO support_tickets (id, user_id, subject, description, priority, category)
        VALUES (:id, :uid, :sub, :desc, :pri, :cat)
    """), {"id": tid, "uid": claims["sub"], "sub": body.subject,
           "desc": body.description, "pri": body.priority, "cat": body.category})
    db.commit()
    return {"ticket_id": tid, "status": "open", "message": "Ticket raised successfully"}

@router.get("/my")
def my_tickets(claims=Depends(require_user), db=Depends(get_db)):
    rows = db.execute(text("""
        SELECT * FROM support_tickets WHERE user_id=:uid ORDER BY created_at DESC
    """), {"uid": claims["sub"]}).fetchall()
    return {"tickets": [dict(r._mapping) for r in rows]}

@router.get("/admin/all")
def all_tickets(status: str = None, claims=Depends(require_admin), db=Depends(get_db)):
    query = """
        SELECT t.*, u.name as user_name, u.company, u.email as user_email
        FROM support_tickets t
        JOIN app_users u ON u.id = t.user_id
    """
    params = {}
    if status:
        query += " WHERE t.status = :status"
        params["status"] = status
    query += " ORDER BY CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, t.created_at DESC"
    rows = db.execute(text(query), params).fetchall()
    return {"tickets": [dict(r._mapping) for r in rows]}

@router.put("/admin/{ticket_id}/respond")
def respond_to_ticket(ticket_id: str, body: TicketResponse,
                       claims=Depends(require_admin), db=Depends(get_db)):
    db.execute(text("""
        UPDATE support_tickets
        SET admin_response=:resp, status=:status, resolved_by=:by, updated_at=NOW()
        WHERE id=:tid
    """), {"resp": body.admin_response, "status": body.status,
           "by": claims["sub"], "tid": ticket_id})
    db.commit()
    return {"success": True, "ticket_id": ticket_id, "status": body.status}
```

### 3.5 — Create `server/routers/lstm_control.py`

```python
"""Admin-only LSTM model management and retraining endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import text
from pydantic import BaseModel
from server.auth import require_admin
from server.db import get_db
import subprocess, os

router = APIRouter(prefix="/api/v1/lstm", tags=["LSTM Control"])

class LSTMConfig(BaseModel):
    name: str
    description: str
    sequence_length: int = 60
    hidden_units: int = 128
    num_layers: int = 2
    dropout: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100

class LSTMHyperparams(BaseModel):
    prediction_window_s: int = 60
    health_threshold: int = 70
    confidence_threshold: float = 0.85
    brownout_sensitivity: float = 0.7

@router.get("/models")
def list_models(claims=Depends(require_admin), db=Depends(get_db)):
    rows = db.execute(text("SELECT * FROM lstm_model_configs ORDER BY created_at DESC")).fetchall()
    return {"models": [dict(r._mapping) for r in rows]}

@router.post("/models")
def create_model(body: LSTMConfig, claims=Depends(require_admin), db=Depends(get_db)):
    import uuid
    mid = f"lstm-{uuid.uuid4().hex[:6]}"
    db.execute(text("""
        INSERT INTO lstm_model_configs
        (id,name,description,sequence_length,hidden_units,num_layers,dropout,learning_rate,batch_size,epochs)
        VALUES (:id,:n,:d,:sl,:hu,:nl,:do,:lr,:bs,:ep)
    """), {"id": mid, "n": body.name, "d": body.description, "sl": body.sequence_length,
           "hu": body.hidden_units, "nl": body.num_layers, "do": body.dropout,
           "lr": body.learning_rate, "bs": body.batch_size, "ep": body.epochs})
    db.commit()
    return {"model_id": mid, "status": "created"}

@router.post("/models/{model_id}/activate")
def activate_model(model_id: str, claims=Depends(require_admin), db=Depends(get_db)):
    db.execute(text("UPDATE lstm_model_configs SET is_active=FALSE"))
    db.execute(text("UPDATE lstm_model_configs SET is_active=TRUE WHERE id=:id"), {"id": model_id})
    db.commit()
    return {"success": True, "active_model": model_id}

@router.post("/retrain")
def trigger_retrain(model_id: str, bg: BackgroundTasks,
                     claims=Depends(require_admin), db=Depends(get_db)):
    def _run_retrain():
        subprocess.Popen(["python", "ml/train_lstm.py", "--model-id", model_id],
                         cwd=os.getcwd())
    bg.add_task(_run_retrain)
    return {"status": "retrain_started", "model_id": model_id,
            "message": "Training job queued. Check logs for progress."}

@router.put("/hyperparams")
def update_hyperparams(body: LSTMHyperparams, claims=Depends(require_admin)):
    """Live-update LSTM inference parameters without retraining."""
    os.environ["PREDICTION_WINDOW_S"] = str(body.prediction_window_s)
    os.environ["HEALTH_THRESHOLD"]    = str(body.health_threshold)
    return {"success": True, "applied": body.dict()}

@router.get("/performance")
def lstm_performance(claims=Depends(require_admin), db=Depends(get_db)):
    """Return accuracy metrics for all models."""
    rows = db.execute(text("""
        SELECT id, name, accuracy, mae_latency, is_active, created_at
        FROM lstm_model_configs ORDER BY created_at DESC
    """)).fetchall()
    return {"models": [dict(r._mapping) for r in rows]}
```

### 3.6 — Create `server/routers/profile.py`

```python
"""User profile view and update endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from pydantic import BaseModel
from server.auth import require_user
from server.db import get_db

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])

class ProfileUpdate(BaseModel):
    name: str = None
    company: str = None
    industry: str = None

@router.get("/")
def get_profile(claims=Depends(require_user), db=Depends(get_db)):
    user = db.execute(text("SELECT * FROM app_users WHERE id=:id"),
                      {"id": claims["sub"]}).fetchone()
    sub = db.execute(text("SELECT * FROM subscriptions WHERE user_id=:id"),
                     {"id": claims["sub"]}).fetchone()
    sites = db.execute(text("SELECT * FROM sites WHERE user_id=:id"),
                       {"id": claims["sub"]}).fetchall()
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "company": user.company, "industry": user.industry,
        "avatar_initials": user.avatar_initials,
        "role": user.role, "created_at": str(user.created_at),
        "subscription": dict(sub._mapping) if sub else None,
        "sites": [dict(s._mapping) for s in sites]
    }

@router.put("/")
def update_profile(body: ProfileUpdate, claims=Depends(require_user), db=Depends(get_db)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"success": True}
    set_clause = ", ".join(f"{k}=:{k}" for k in updates)
    updates["id"] = claims["sub"]
    db.execute(text(f"UPDATE app_users SET {set_clause} WHERE id=:id"), updates)
    db.commit()
    return {"success": True}
```

### 3.7 — Create `server/routers/admin.py` (user management + analytics)

```python
"""Admin portal — user management, site analytics, platform overview."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from server.auth import require_admin
from server.db import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.get("/users")
def list_all_users(claims=Depends(require_admin), db=Depends(get_db)):
    rows = db.execute(text("""
        SELECT u.id, u.name, u.email, u.company, u.industry, u.role,
               u.is_active, u.created_at,
               s.plan_name, s.monthly_price, s.status as sub_status,
               (SELECT COUNT(*) FROM sites WHERE user_id=u.id) as site_count,
               (SELECT COUNT(*) FROM support_tickets WHERE user_id=u.id AND status='open') as open_tickets
        FROM app_users u
        LEFT JOIN subscriptions s ON s.user_id = u.id
        WHERE u.role != 'SUPER_ADMIN'
        ORDER BY u.created_at DESC
    """)).fetchall()
    return {"users": [dict(r._mapping) for r in rows]}

@router.get("/users/{user_id}/analytics")
def user_site_analytics(user_id: str, hours: int = 24,
                          claims=Depends(require_admin), db=Depends(get_db)):
    """Return last N hours of telemetry summary for all sites of a user."""
    rows = db.execute(text("""
        SELECT s.name as site_name, t.link_type,
               ROUND(AVG(t.latency_ms)::numeric, 2) as avg_latency,
               ROUND(AVG(t.health_score)::numeric, 1) as avg_health,
               ROUND(AVG(t.packet_loss_pct)::numeric, 4) as avg_loss,
               COUNT(*) as data_points
        FROM telemetry_live t
        JOIN sites s ON s.id = t.site_id
        WHERE s.user_id = :uid
          AND t.timestamp > NOW() - INTERVAL ':hours hours'
        GROUP BY s.name, t.link_type
        ORDER BY avg_health ASC
    """), {"uid": user_id, "hours": hours}).fetchall()
    return {"user_id": user_id, "window_hours": hours,
            "analytics": [dict(r._mapping) for r in rows]}

@router.get("/platform/overview")
def platform_overview(claims=Depends(require_admin), db=Depends(get_db)):
    """High-level platform health for admin dashboard."""
    stats = db.execute(text("""
        SELECT
          (SELECT COUNT(*) FROM app_users WHERE role != 'SUPER_ADMIN') as total_users,
          (SELECT COUNT(*) FROM app_users WHERE role != 'SUPER_ADMIN' AND is_active=TRUE) as active_users,
          (SELECT COUNT(*) FROM sites) as total_sites,
          (SELECT COALESCE(SUM(monthly_price),0) FROM subscriptions WHERE status='active') as mrr,
          (SELECT COUNT(*) FROM support_tickets WHERE status='open') as open_tickets,
          (SELECT COUNT(*) FROM support_tickets WHERE status='open' AND priority='high') as urgent_tickets
    """)).fetchone()
    return dict(stats._mapping)

@router.put("/users/{user_id}/suspend")
def suspend_user(user_id: str, claims=Depends(require_admin), db=Depends(get_db)):
    db.execute(text("UPDATE app_users SET is_active=FALSE WHERE id=:id"), {"id": user_id})
    db.commit()
    return {"success": True, "user_id": user_id, "status": "suspended"}

@router.put("/users/{user_id}/reactivate")
def reactivate_user(user_id: str, claims=Depends(require_admin), db=Depends(get_db)):
    db.execute(text("UPDATE app_users SET is_active=TRUE, failed_attempts=0, locked_until=NULL WHERE id=:id"),
               {"id": user_id})
    db.commit()
    return {"success": True, "user_id": user_id, "status": "active"}
```

### 3.8 — Register all new routers in `server/main.py`

```python
# Add to existing router registrations
from server.routers import billing, tickets, lstm_control, profile, admin as admin_router

app.include_router(billing.router)
app.include_router(tickets.router)
app.include_router(lstm_control.router)
app.include_router(profile.router)
app.include_router(admin_router.router)
```

---

## SECTION 4 — SHARED UI COMPONENTS

### 4.1 — TypeScript type definitions (`frontend/src/types/index.ts`)

```typescript
export type UserRole = 'SUPER_ADMIN' | 'BUSINESS_OWNER';

export interface AuthUser {
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  company?: string;
  avatar_initials: string;
  access_token: string;
  redirect_to: string;
}

export interface Subscription {
  id: string;
  plan_id: string;
  plan_name: string;
  status: 'active' | 'cancelled' | 'past_due';
  monthly_price: number;
  next_billing_date: string;
  card_last4: string;
}

export interface SupportTicket {
  id: string;
  subject: string;
  description: string;
  priority: 'low' | 'medium' | 'high';
  status: 'open' | 'in_progress' | 'resolved';
  category: string;
  admin_response?: string;
  created_at: string;
  updated_at: string;
}

export interface Site {
  id: string;
  name: string;
  location: string;
  status: string;
}

export interface TelemetryPoint {
  site_id: string;
  link_type: string;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  health_score: number;
  bandwidth_mbps: number;
  timestamp: string;
}

export interface LSTMModel {
  id: string;
  name: string;
  description: string;
  sequence_length: number;
  hidden_units: number;
  num_layers: number;
  dropout: number;
  learning_rate: number;
  is_active: boolean;
  accuracy?: number;
  mae_latency?: number;
  created_at: string;
}

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  company: string;
  industry: string;
  plan_name: string;
  monthly_price: number;
  sub_status: string;
  site_count: number;
  open_tickets: number;
  is_active: boolean;
}
```

### 4.2 — Auth Context (`frontend/src/context/AuthContext.tsx`)

```tsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import type { AuthUser } from '../types';

interface AuthCtx {
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthCtx>(null!);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('pathwise_user');
    if (stored) setUser(JSON.parse(stored));
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    const authUser: AuthUser = { ...data };
    localStorage.setItem('pathwise_user', JSON.stringify(authUser));
    setUser(authUser);
  };

  const logout = () => {
    localStorage.removeItem('pathwise_user');
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAdmin: user?.role === 'SUPER_ADMIN', isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### 4.3 — API Client (`frontend/src/utils/apiClient.ts`)

```typescript
const BASE = '/api/v1';

function getToken(): string {
  const stored = localStorage.getItem('pathwise_user');
  return stored ? JSON.parse(stored).access_token : '';
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...options.headers,
    },
  });
  if (res.status === 401) { window.location.href = '/login'; }
  if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Request failed'); }
  return res.json();
}

export const api = {
  get:    <T>(path: string) => request<T>(path),
  post:   <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT',  body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
```

---

## SECTION 5 — SHARED LOGIN PAGE

### 5.1 — `frontend/src/pages/auth/LoginPage.tsx`

Build a full-screen dark-themed login page. Requirements from SDD §8 UI-1:
- PathWise AI logo / wordmark centered
- Subtitle: "Intelligent SD-WAN Management"
- Email + password fields
- "Sign In" button (blue, full width)
- "TLS 1.3 Encrypted Connection" badge at bottom
- "Account locked after 5 failed attempts" notice
- Error state: generic message, no username enumeration
- On success: redirect to `/admin/dashboard` for SUPER_ADMIN, `/user/dashboard` for BUSINESS_OWNER
- Responsive: works on mobile (min-width: 320px)

```tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('Please fill in all fields.'); return; }
    setLoading(true); setError('');
    try {
      await login(email, password);
      const stored = JSON.parse(localStorage.getItem('pathwise_user')!);
      navigate(stored.redirect_to);
    } catch (err: any) {
      setError('Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      <div style={{
        background: '#1e293b', border: '1px solid #334155', borderRadius: 16,
        padding: '2.5rem', width: '100%', maxWidth: 420
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            marginBottom: 8
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10,
              background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontWeight: 700, fontSize: 18
            }}>P</div>
            <span style={{ color: '#f1f5f9', fontSize: 24, fontWeight: 700 }}>PathWise AI</span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: 14, margin: 0 }}>
            Intelligent SD-WAN Management
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ color: '#94a3b8', fontSize: 13, display: 'block', marginBottom: 6 }}>
              Email address
            </label>
            <input
              type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="admin@company.com" autoComplete="email"
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8,
                border: `1px solid ${error ? '#ef4444' : '#334155'}`,
                background: '#0f172a', color: '#f1f5f9', fontSize: 15,
                outline: 'none', boxSizing: 'border-box'
              }}
            />
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ color: '#94a3b8', fontSize: 13, display: 'block', marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" autoComplete="current-password"
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8,
                border: `1px solid ${error ? '#ef4444' : '#334155'}`,
                background: '#0f172a', color: '#f1f5f9', fontSize: 15,
                outline: 'none', boxSizing: 'border-box'
              }}
            />
          </div>

          {error && (
            <div style={{
              background: '#450a0a', border: '1px solid #ef4444', borderRadius: 8,
              padding: '10px 14px', color: '#fca5a5', fontSize: 14, marginBottom: '1rem'
            }}>{error}</div>
          )}

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '11px', borderRadius: 8, border: 'none',
            background: loading ? '#1d4ed8' : '#2563eb', color: 'white',
            fontSize: 16, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'background 0.2s'
          }}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {/* Footer badges */}
        <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: '#0f2d0f', border: '1px solid #16a34a', borderRadius: 20,
            padding: '4px 12px', color: '#86efac', fontSize: 12
          }}>
            <span style={{ fontSize: 10 }}>🔒</span> TLS 1.3 Encrypted Connection
          </div>
          <p style={{ color: '#475569', fontSize: 12, margin: 0, textAlign: 'center' }}>
            Account locked after 5 failed attempts
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

## SECTION 6 — USER PORTAL (8 pages)

All user pages live under `/user/*` and are wrapped in `UserLayout`.

### 6.1 — `frontend/src/components/layout/UserLayout.tsx`

Left sidebar (dark, 240px) + content area (light). Sidebar items:
- Dashboard (home icon)
- My Sites & Analytics (chart icon)
- Traffic Overview (network icon)
- Billing & Subscription (credit card icon)
- Support Tickets (ticket icon)
- My Profile (person icon)
- Sign Out (at bottom)

Topbar: Company name + avatar initials circle + "PathWise AI" badge top-right.

### 6.2 — `frontend/src/pages/user/UserDashboard.tsx`

**Route:** `/user/dashboard`  
**Purpose:** Overview of the user's own sites and WAN health.

Layout (top to bottom):
1. Welcome banner: "Good morning, {name} — {company}" with current date
2. Summary metric cards (4 in a row):
   - Total Sites (count)
   - Active WAN Links (count)
   - Avg Health Score (0–100, color coded green/amber/red)
   - Alerts Today (count, red badge if > 0)
3. Multi-Link Health Scoreboard for user's own sites only:
   - Card per link showing: link type icon, health score big number, color (green ≥80 / amber 50–79 / red <50), latency, jitter, loss, status badge
   - Site selector tabs at top (one tab per site the user owns)
   - Refreshes via WebSocket at 1 Hz
4. Health Score Timeline chart (Recharts LineChart):
   - Last 30 minutes
   - One line per WAN link, color-coded
   - Dashed line = LSTM prediction (30s ahead)
   - X-axis: time labels
   - Y-axis: 0–100 health score
5. Recent AI Routing Events table:
   - Columns: Time | Event | Link | Confidence | Status
   - Max 10 rows, paginated
   - Badge colors: SUCCESS=green, ACTIVE=amber, VALIDATED=blue

Implementation notes:
- Data comes from `GET /api/v1/telemetry/site/{site_id}` (scoped to user's sites)
- WebSocket: `ws://host/ws/user/{user_id}/telemetry`
- Empty state if no data yet: "Simulator is warming up… data arrives in ~30s"

### 6.3 — `frontend/src/pages/user/MySitesAnalytics.tsx`

**Route:** `/user/sites`  
**Purpose:** Granular per-site, per-link analytics.

Layout:
1. Site selector dropdown (user's sites only)
2. Time range picker: Last 30 min / 1hr / 6hr / 24hr / 7d
3. Four metric charts in a 2×2 grid (Recharts AreaChart):
   - Latency over time (ms)
   - Jitter over time (ms)
   - Packet Loss (%)
   - Bandwidth Utilization (Mbps)
   - Each chart: solid line = actual, dashed = LSTM forecast, shaded region = confidence interval
4. Link Statistics Summary bar at bottom:
   - Uptime % | Handoff Events Today | Avg Health Score | Alerts Triggered | LSTM Inference Cycles | Avg Inference Time
5. Export button: Export CSV / Export PDF (calls `GET /api/v1/telemetry/export?site_id=…&format=csv`)

### 6.4 — `frontend/src/pages/user/TrafficOverview.tsx`

**Route:** `/user/traffic`  
**Purpose:** Show traffic distribution and AI steering events.

Layout:
1. Traffic class distribution donut chart (Recharts PieChart):
   - Slices: VoIP / Video / Critical / Bulk / Other
   - Legend with percentages
2. Current routing table:
   - Columns: Traffic Class | Current Path | Backup Path | Status | Last Steering
   - Status badge: ACTIVE / STANDBY / FAILOVER
3. Recent steering events timeline (vertical feed):
   - Each event: icon + timestamp + "VoIP rerouted from Fiber → 5G (Sandbox: PASS, Confidence: 94%)"
   - Color: green for success, amber for in-progress

### 6.5 — `frontend/src/pages/user/BillingDashboard.tsx`

**Route:** `/user/billing`  
**Purpose:** Subscription management, invoices, payment.

Layout sections (tabs):

**Tab 1 — Current Plan:**
- Plan name badge (e.g., "Professional") with color
- Price: "$149/month"
- Next billing date
- Payment method: "Visa ending in 4242" + card icon
- Features list with checkmarks
- Two action buttons:
  - "Upgrade Plan" → opens plan comparison modal
  - "Cancel Subscription" → confirms with modal ("Are you sure?")

**Tab 2 — Change Plan (Plan Comparison):**
- Three plan cards side by side: Starter / Professional / Enterprise
- Each card shows: price, site limit, features list, checkmarks
- Current plan highlighted with blue border + "Current Plan" badge
- "Select Plan" button on non-current plans → calls `POST /api/v1/billing/subscription/upgrade`
- Plans data from `GET /api/v1/billing/plans`

**Tab 3 — Invoice History:**
- Table: Invoice # | Period | Amount | Status | Download
- Status badge: Paid=green, Pending=amber, Overdue=red
- Download button: calls invoice PDF endpoint (stub if not implemented: show "Coming soon")
- Empty state: "No invoices yet"

### 6.6 — `frontend/src/pages/user/SupportTickets.tsx`

**Route:** `/user/tickets`  
**Purpose:** Raise and track support tickets.

Layout:
1. "Raise a Ticket" button (top right, primary blue)
2. Ticket list (cards):
   - Each card: Ticket ID | Subject | Category | Priority badge | Status badge | Date | "View" button
   - Priority colors: High=red, Medium=amber, Low=blue
   - Status colors: Open=amber, In Progress=purple, Resolved=green
3. "Raise Ticket" modal/form (opens on button click):
   - Fields:
     - Subject (text input, required)
     - Category (dropdown: General / Network Issue / Billing / Feature Request / Bug Report / Compliance)
     - Priority (radio: Low / Medium / High)
     - Description (textarea, min 20 chars)
   - Submit: calls `POST /api/v1/tickets/`
   - Success toast: "Ticket #{id} raised successfully. We'll respond within 24 hours."
4. Ticket detail view (expand on click):
   - Full description
   - Admin response (if any): shown in blue-tinted box with "PathWise Support" label
   - Status timeline dots

### 6.7 — `frontend/src/pages/user/UserProfile.tsx`

**Route:** `/user/profile`  
**Purpose:** View and edit user profile.

Layout:
1. Profile header card:
   - Large avatar circle (initials, colored by role)
   - Name, email, company
   - "Member since" date
   - Plan badge
2. Edit form (inline, toggle with "Edit Profile" button):
   - Name (text)
   - Company (text)
   - Industry (dropdown: Logistics / Healthcare / Retail / Education / Manufacturing / Finance / Hospitality / Technology / Other)
   - Save button: calls `PUT /api/v1/profile/`
   - Read-only fields: Email, Role, Account ID
3. Account stats section:
   - Sites Registered
   - Total Tickets Raised
   - Account Status (Active / Suspended)
4. Security section:
   - "Change Password" button (leads to modal with current + new password + confirm)
   - "Active Sessions" (static: "1 active session — current browser")
5. Danger Zone (red-bordered section):
   - "Contact Support to Delete Account" link → opens pre-filled ticket

---

## SECTION 7 — ADMIN PORTAL (7 pages)

All admin pages live under `/admin/*` and are wrapped in `AdminLayout`.

### 7.1 — `frontend/src/components/layout/AdminLayout.tsx`

Left sidebar (dark navy #0f172a, 260px) + content area (slate-50 background).  
Sidebar header: "PathWise AI" wordmark + "Admin Portal" subtitle.  
Sidebar items:
- Platform Overview (grid icon)
- User Management (users icon)
- Site Analytics (chart-bar icon)
- Revenue Dashboard (currency-dollar icon)
- LSTM Control Center (cpu icon)
- Support Tickets (chat-bubble icon)
- Audit Log (document-text icon)
- Sign Out (bottom)

Top bar: Shows "Administrator" role badge + admin name + avatar.

### 7.2 — `frontend/src/pages/admin/AdminDashboard.tsx`

**Route:** `/admin/dashboard`  
**Purpose:** Platform-wide overview at a glance.

Layout:
1. Summary metric cards (6 in 2 rows of 3):
   - Total Users (count, link to user management)
   - Active Subscriptions (count)
   - Monthly Recurring Revenue ("$XXX")
   - Total Sites Monitored (count)
   - Open Support Tickets (count, red if > 0)
   - Platform Uptime ("99.97%")
   - Data from `GET /api/v1/admin/platform/overview`
2. Per-user health status table:
   - Columns: User | Company | Industry | Plan | Sites | Avg Health | Status | Open Tickets | Actions
   - "View Analytics" button per row
   - Color-code Avg Health: green/amber/red
   - Sortable columns
3. Urgent Alerts feed:
   - Right column, 300px wide
   - List of high-priority open tickets and sites with health < 50
   - Each item: time + user + issue
4. Revenue mini-chart (Recharts BarChart):
   - Monthly revenue last 6 months
   - Data from `GET /api/v1/billing/admin/revenue`

### 7.3 — `frontend/src/pages/admin/UserManagement.tsx`

**Route:** `/admin/users`  
**Purpose:** Full user account control panel.

Layout:
1. Search bar (search by name, email, company)
2. Filter chips: All / Active / Suspended / By Plan (Starter / Pro / Enterprise)
3. User table (each row expandable):
   - Avatar initials circle
   - Name + email
   - Company + Industry badge
   - Plan badge
   - Sites count
   - MRR amount
   - Status (Active/Suspended) badge
   - Open tickets badge
   - Action menu (three dots):
     - View Full Analytics
     - Suspend Account → `PUT /api/v1/admin/users/{id}/suspend`
     - Reactivate Account → `PUT /api/v1/admin/users/{id}/reactivate`
     - Unlock Account (if locked)
     - View Tickets
4. "Add New User" button → modal with: name, email, password, company, industry, plan selector
5. User detail drawer (slides from right on row click):
   - Full profile info
   - Subscription history
   - Site list with health scores
   - Ticket history

### 7.4 — `frontend/src/pages/admin/SiteAnalytics.tsx`

**Route:** `/admin/analytics`  
**Purpose:** Admin views ALL users' site telemetry.

Layout:
1. User selector dropdown (all 8 users)
2. Site selector (filtered by selected user's sites)
3. Time range picker
4. Same 4-chart layout as user's analytics page but for ANY user's data
5. Cross-user comparison table:
   - All users + all sites + current avg health + trend arrow (improving/stable/degrading)
   - Sortable by health score
6. "Export All Analytics" button → CSV download

### 7.5 — `frontend/src/pages/admin/RevenueDashboard.tsx`

**Route:** `/admin/revenue`  
**Purpose:** Financial analytics.

Layout:
1. Top KPI row (4 cards):
   - Total MRR (e.g., "$1,293/mo")
   - ARR ("$15,516/yr")
   - Avg Revenue Per User (ARPU)
   - Active Paying Users
2. Revenue by Plan (Recharts PieChart):
   - Slices: Starter / Professional / Enterprise
   - Shows count + revenue
3. Monthly Revenue Trend (Recharts BarChart):
   - Last 12 months
   - Bars colored by growth (green if up, amber if flat, red if down)
4. User subscription table:
   - All users with plan, price, next billing date, status
   - Sorted by revenue DESC

### 7.6 — `frontend/src/pages/admin/LSTMControlCenter.tsx`

**Route:** `/admin/lstm`  
**Purpose:** Admin control panel for LSTM models — the only place where internal LSTM behavior can be modified.

Layout (3 tabs):

**Tab 1 — Active Model:**
- Current model info card:
  - Name, description, accuracy %, MAE
  - Architecture summary: Sequence length / Hidden units / Layers / Dropout
  - Status: ACTIVE badge (green)
  - "Retrain with Current Config" button → `POST /api/v1/lstm/retrain`
  - Retrain status spinner with "Training in progress… check back in a few minutes"
- Inference parameter sliders (live-adjustable):
  - Prediction Window (30–120 s) slider → `PUT /api/v1/lstm/hyperparams`
  - Health Score Threshold (50–90) slider
  - Confidence Threshold (0.5–0.99) slider
  - Brownout Sensitivity (0.3–1.0) slider
  - All sliders show current value, call API on change with 500ms debounce
  - "Apply Changes" button (calls API immediately)

**Tab 2 — Model Library:**
- Table of all saved model configs:
  - Name | Architecture summary | Accuracy | MAE | Status | Created | Actions
  - "Set Active" button → `POST /api/v1/lstm/models/{id}/activate`
  - "Delete" button (disabled for active model)
- "Create New Model Config" form:
  - Fields: Name, Description, Sequence Length, Hidden Units, Layers, Dropout, Learning Rate, Batch Size, Epochs
  - Input validation: all numeric, ranges shown in placeholders
  - Submit → `POST /api/v1/lstm/models`
  - "Start Training" → `POST /api/v1/lstm/retrain?model_id=…`

**Tab 3 — Performance Comparison:**
- Side-by-side accuracy bars for all models
- Recharts BarChart: model names on X, accuracy % on Y
- MAE comparison table: latency / jitter / packet loss MAE per model
- Training history log (static table for now): Model | Date Trained | Epochs | Final Loss | Accuracy

### 7.7 — `frontend/src/pages/admin/TicketDashboard.tsx`

**Route:** `/admin/tickets`  
**Purpose:** Admin manages all user support tickets.

Layout:
1. Stats row:
   - Open | In Progress | Resolved (counts with colored badges)
   - High Priority open tickets (red badge)
2. Filter tabs: All | Open | In Progress | Resolved
3. Priority filter: All | High | Medium | Low
4. Ticket queue (table):
   - Columns: Ticket ID | User | Company | Subject | Category | Priority | Status | Raised | Actions
   - Sorted by: High priority first, then oldest first (SLA order)
   - "Respond" button per row → opens response modal
5. Response modal:
   - Shows: user name + company, full description, category, priority
   - "Admin Response" textarea (required, min 20 chars)
   - Status selector: In Progress / Resolved
   - "Send Response" → `PUT /api/v1/tickets/admin/{id}/respond`
   - Success toast: "Response sent. User notified."
6. Resolved tickets tab: read-only view with response shown

---

## SECTION 8 — ROUTING AND APP ENTRY

### 8.1 — `frontend/src/App.tsx`

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/auth/LoginPage';

// Admin pages
import AdminDashboard    from './pages/admin/AdminDashboard';
import UserManagement    from './pages/admin/UserManagement';
import SiteAnalytics     from './pages/admin/SiteAnalytics';
import RevenueDashboard  from './pages/admin/RevenueDashboard';
import LSTMControlCenter from './pages/admin/LSTMControlCenter';
import TicketDashboard   from './pages/admin/TicketDashboard';

// User pages
import UserDashboard    from './pages/user/UserDashboard';
import MySitesAnalytics from './pages/user/MySitesAnalytics';
import TrafficOverview  from './pages/user/TrafficOverview';
import BillingDashboard from './pages/user/BillingDashboard';
import SupportTickets   from './pages/user/SupportTickets';
import UserProfile      from './pages/user/UserProfile';

// Guards
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isAdmin, isLoading } = useAuth();
  if (isLoading) return <div>Loading…</div>;
  if (!user) return <Navigate to="/login" />;
  if (!isAdmin) return <Navigate to="/user/dashboard" />;
  return <>{children}</>;
};

const UserRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div>Loading…</div>;
  if (!user) return <Navigate to="/login" />;
  return <>{children}</>;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/login" />} />

          {/* Admin routes */}
          <Route path="/admin/dashboard"  element={<AdminRoute><AdminDashboard /></AdminRoute>} />
          <Route path="/admin/users"      element={<AdminRoute><UserManagement /></AdminRoute>} />
          <Route path="/admin/analytics"  element={<AdminRoute><SiteAnalytics /></AdminRoute>} />
          <Route path="/admin/revenue"    element={<AdminRoute><RevenueDashboard /></AdminRoute>} />
          <Route path="/admin/lstm"       element={<AdminRoute><LSTMControlCenter /></AdminRoute>} />
          <Route path="/admin/tickets"    element={<AdminRoute><TicketDashboard /></AdminRoute>} />

          {/* User routes */}
          <Route path="/user/dashboard" element={<UserRoute><UserDashboard /></UserRoute>} />
          <Route path="/user/sites"     element={<UserRoute><MySitesAnalytics /></UserRoute>} />
          <Route path="/user/traffic"   element={<UserRoute><TrafficOverview /></UserRoute>} />
          <Route path="/user/billing"   element={<UserRoute><BillingDashboard /></UserRoute>} />
          <Route path="/user/tickets"   element={<UserRoute><SupportTickets /></UserRoute>} />
          <Route path="/user/profile"   element={<UserRoute><UserProfile /></UserRoute>} />

          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

---

## SECTION 9 — DESIGN SYSTEM CONSTANTS

Apply these consistently across all pages. Put in `frontend/src/utils/theme.ts`:

```typescript
export const colors = {
  // Backgrounds
  bgDark:     '#0f172a',   // sidebar, login bg
  bgMid:      '#1e293b',   // card bg in dark areas
  bgLight:    '#f8fafc',   // main content area
  bgCard:     '#ffffff',   // content cards

  // Brand
  primary:    '#2563eb',   // buttons, links, active nav
  primaryHov: '#1d4ed8',

  // Health status (from SDD)
  healthy:    '#16a34a',   // score ≥ 80
  warning:    '#d97706',   // score 50–79
  critical:   '#dc2626',   // score < 50

  // Text
  textPrimary:   '#0f172a',
  textSecondary: '#64748b',
  textInverse:   '#f1f5f9',

  // Borders
  border:     '#e2e8f0',
  borderDark: '#334155',
};

export const healthColor = (score: number): string => {
  if (score >= 80) return colors.healthy;
  if (score >= 50) return colors.warning;
  return colors.critical;
};

export const priorityColor = (p: string): string =>
  ({ high: '#ef4444', medium: '#f59e0b', low: '#3b82f6' })[p] ?? '#6b7280';

export const statusColor = (s: string): string =>
  ({ open: '#f59e0b', in_progress: '#8b5cf6', resolved: '#16a34a',
     active: '#16a34a', cancelled: '#ef4444', past_due: '#f59e0b' })[s] ?? '#6b7280';
```

---

## SECTION 10 — WEBSOCKET INTEGRATION

### 10.1 — Backend WebSocket for per-user live telemetry (`server/websocket.py`)

Add to `server/main.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect
from server.auth import verify_token

@app.websocket("/ws/user/{user_id}/telemetry")
async def user_telemetry_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            # Fetch latest telemetry for user's sites
            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT t.site_id, t.link_type, t.latency_ms, t.jitter_ms,
                           t.packet_loss_pct, t.health_score, t.bandwidth_mbps,
                           t.timestamp
                    FROM telemetry_live t
                    JOIN sites s ON s.id = t.site_id
                    WHERE s.user_id = :uid
                      AND t.timestamp = (
                          SELECT MAX(t2.timestamp) FROM telemetry_live t2
                          WHERE t2.site_id = t.site_id AND t2.link_type = t.link_type
                      )
                    ORDER BY t.site_id, t.link_type
                """), {"uid": user_id}).fetchall()

            payload = [dict(r._mapping) for r in rows]
            await websocket.send_json({"type": "telemetry", "data": payload,
                                       "ts": datetime.utcnow().isoformat()})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
```

### 10.2 — Frontend WebSocket hook (`frontend/src/hooks/useUserTelemetry.ts`)

```typescript
import { useEffect, useState, useRef } from 'react';
import type { TelemetryPoint } from '../types';

export function useUserTelemetry(userId: string) {
  const [data, setData] = useState<TelemetryPoint[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!userId) return;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/user/${userId}/telemetry`);
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'telemetry') setData(msg.data);
    };

    return () => ws.close();
  }, [userId]);

  return { data, connected };
}
```

---

## SECTION 11 — TEST CASES

### 11.1 — `tests/ui/test_auth_roles.py`

```python
"""
UI Test Suite — Authentication and Role-Based Access Control
All login credentials tested. Admin/user route separation verified.
"""
import pytest
import httpx

BASE = "http://localhost:8000"

ADMIN_CREDS   = {"email": "admin@pathwise.ai",        "password": "Admin@PathWise2026"}
USER_CREDS    = [
    {"email": "marcus@riveralogistics.com",  "password": "Rivera@2026"},
    {"email": "priya@nairmedical.com",       "password": "NairMed@2026"},
    {"email": "deshawn@carterretail.com",    "password": "Carter@2026"},
    {"email": "sofia@moralesacademy.edu",    "password": "Sofia@2026"},
    {"email": "kenji@tanakafab.com",         "password": "Tanaka@2026"},
    {"email": "amara@oseifinance.com",       "password": "Amara@2026"},
    {"email": "elena@petrovhotel.com",       "password": "Elena@2026"},
    {"email": "tobias@bauertech.io",         "password": "Bauer@2026"},
]

def _login(creds: dict) -> dict:
    r = httpx.post(f"{BASE}/api/v1/auth/login", json=creds)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.text}"
    return r.json()

def test_admin_login_returns_admin_role():
    data = _login(ADMIN_CREDS)
    assert data["role"] == "SUPER_ADMIN"
    assert data["redirect_to"] == "/admin/dashboard"

@pytest.mark.parametrize("creds", USER_CREDS)
def test_all_8_users_can_login(creds):
    data = _login(creds)
    assert data["role"] == "BUSINESS_OWNER"
    assert data["redirect_to"] == "/user/dashboard"
    assert "access_token" in data

def test_all_9_accounts_have_distinct_tokens():
    all_creds = [ADMIN_CREDS] + USER_CREDS
    tokens = [_login(c)["access_token"] for c in all_creds]
    assert len(set(tokens)) == 9, "All tokens must be unique"

def test_admin_token_accesses_admin_route():
    data = _login(ADMIN_CREDS)
    token = data["access_token"]
    r = httpx.get(f"{BASE}/api/v1/admin/platform/overview",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

def test_user_token_cannot_access_admin_route():
    data = _login(USER_CREDS[0])
    token = data["access_token"]
    r = httpx.get(f"{BASE}/api/v1/admin/platform/overview",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, "User must not access admin endpoints"

def test_admin_token_can_access_user_routes():
    data = _login(ADMIN_CREDS)
    token = data["access_token"]
    r = httpx.get(f"{BASE}/api/v1/profile/",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

def test_invalid_credentials_return_401():
    r = httpx.post(f"{BASE}/api/v1/auth/login",
                   json={"email": "nobody@fake.com", "password": "wrong"})
    assert r.status_code == 401

def test_wrong_password_returns_generic_error():
    r = httpx.post(f"{BASE}/api/v1/auth/login",
                   json={"email": ADMIN_CREDS["email"], "password": "wrongpassword"})
    assert r.status_code == 401
    body = r.json()
    assert "Invalid credentials" in body["detail"]
    assert "password" not in body["detail"].lower()   # no username enumeration
```

### 11.2 — `tests/ui/test_billing_api.py`

```python
"""Billing API tests — subscriptions, invoices, plan changes."""
import pytest, httpx

BASE = "http://localhost:8000"

def _token(email, pw):
    r = httpx.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": pw})
    return r.json()["access_token"]

@pytest.fixture(scope="module")
def user1_token():
    return _token("marcus@riveralogistics.com", "Rivera@2026")

def test_get_subscription(user1_token):
    r = httpx.get(f"{BASE}/api/v1/billing/subscription",
                  headers={"Authorization": f"Bearer {user1_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "plan_name" in data
    assert "monthly_price" in data

def test_get_plans_public():
    r = httpx.get(f"{BASE}/api/v1/billing/plans")
    assert r.status_code == 200
    plans = r.json()["plans"]
    assert len(plans) == 3
    plan_ids = [p["id"] for p in plans]
    assert "starter" in plan_ids
    assert "professional" in plan_ids
    assert "enterprise" in plan_ids

def test_upgrade_plan(user1_token):
    r = httpx.post(f"{BASE}/api/v1/billing/subscription/upgrade",
                   json={"plan_id": "enterprise"},
                   headers={"Authorization": f"Bearer {user1_token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True

def test_get_invoices(user1_token):
    r = httpx.get(f"{BASE}/api/v1/billing/invoices",
                  headers={"Authorization": f"Bearer {user1_token}"})
    assert r.status_code == 200
    invoices = r.json()["invoices"]
    assert isinstance(invoices, list)

def test_admin_revenue_dashboard():
    admin_token = _token("admin@pathwise.ai", "Admin@PathWise2026")
    r = httpx.get(f"{BASE}/api/v1/billing/admin/revenue",
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total_mrr" in data
    assert "arr" in data
    assert data["total_mrr"] > 0

def test_user_cannot_access_revenue_dashboard(user1_token):
    r = httpx.get(f"{BASE}/api/v1/billing/admin/revenue",
                  headers={"Authorization": f"Bearer {user1_token}"})
    assert r.status_code == 403
```

### 11.3 — `tests/ui/test_tickets_api.py`

```python
"""Support ticket API tests."""
import pytest, httpx, uuid

BASE = "http://localhost:8000"

def _token(email, pw):
    return httpx.post(f"{BASE}/api/v1/auth/login",
                      json={"email": email, "password": pw}).json()["access_token"]

@pytest.fixture(scope="module")
def user_token():
    return _token("deshawn@carterretail.com", "Carter@2026")

@pytest.fixture(scope="module")
def admin_token():
    return _token("admin@pathwise.ai", "Admin@PathWise2026")

def test_user_can_raise_ticket(user_token):
    r = httpx.post(f"{BASE}/api/v1/tickets/",
                   json={"subject": "Test ticket from pytest",
                         "description": "This is a test ticket raised by automated tests.",
                         "priority": "low", "category": "general"},
                   headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    assert "ticket_id" in r.json()

def test_user_sees_own_tickets(user_token):
    r = httpx.get(f"{BASE}/api/v1/tickets/my",
                  headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200
    assert isinstance(r.json()["tickets"], list)

def test_admin_sees_all_tickets(admin_token):
    r = httpx.get(f"{BASE}/api/v1/tickets/admin/all",
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    tickets = r.json()["tickets"]
    assert len(tickets) >= 1

def test_admin_can_respond(admin_token, user_token):
    # First raise a ticket
    t = httpx.post(f"{BASE}/api/v1/tickets/",
                   json={"subject": "Respond test", "description": "Testing admin response flow here.",
                         "priority": "medium", "category": "general"},
                   headers={"Authorization": f"Bearer {user_token}"}).json()
    tid = t["ticket_id"]

    r = httpx.put(f"{BASE}/api/v1/tickets/admin/{tid}/respond",
                  json={"admin_response": "We have reviewed your ticket and resolved the issue.",
                        "status": "resolved"},
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"

def test_user_cannot_respond_to_tickets(user_token):
    r = httpx.put(f"{BASE}/api/v1/tickets/admin/ticket-001/respond",
                  json={"admin_response": "Unauthorized response attempt", "status": "resolved"},
                  headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 403
```

### 11.4 — `tests/ui/test_continuous_data.py`

```python
"""
Verify continuous simulator is generating data for all user sites.
"""
import time, pytest, httpx

BASE = "http://localhost:8000"

def _token(email, pw):
    return httpx.post(f"{BASE}/api/v1/auth/login",
                      json={"email": email, "password": pw}).json()["access_token"]

USER_EMAILS = [
    ("marcus@riveralogistics.com", "Rivera@2026"),
    ("priya@nairmedical.com",      "NairMed@2026"),
    ("deshawn@carterretail.com",   "Carter@2026"),
]

@pytest.mark.parametrize("email,pw", USER_EMAILS)
def test_user_has_live_telemetry_data(email, pw):
    """Each user must have ≥1 telemetry row in the last 60 seconds."""
    from sqlalchemy import create_engine, text
    import os
    engine = create_engine(os.getenv("DATABASE_URL","postgresql://pathwise:pathwise@localhost:5432/pathwise"))
    with engine.connect() as conn:
        count = conn.execute(text("""
            SELECT COUNT(*) FROM telemetry_live t
            JOIN sites s ON s.id = t.site_id
            JOIN app_users u ON u.id = s.user_id
            WHERE u.email = :email
              AND t.timestamp > NOW() - INTERVAL '60 seconds'
        """), {"email": email}).scalar()
    assert count > 0, f"No live data for {email} — is the simulator running?"

def test_admin_can_see_all_users_analytics():
    admin_token = _token("admin@pathwise.ai", "Admin@PathWise2026")
    r = httpx.get(f"{BASE}/api/v1/admin/users",
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    users = r.json()["users"]
    assert len(users) == 8, f"Expected 8 users, got {len(users)}"
```

### 11.5 — `tests/ui/test_lstm_control.py`

```python
"""Admin LSTM control center tests."""
import pytest, httpx

BASE = "http://localhost:8000"

@pytest.fixture(scope="module")
def admin_token():
    r = httpx.post(f"{BASE}/api/v1/auth/login",
                   json={"email": "admin@pathwise.ai", "password": "Admin@PathWise2026"})
    return r.json()["access_token"]

def test_list_lstm_models(admin_token):
    r = httpx.get(f"{BASE}/api/v1/lstm/models",
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    models = r.json()["models"]
    assert len(models) >= 1

def test_create_lstm_model(admin_token):
    r = httpx.post(f"{BASE}/api/v1/lstm/models",
                   json={"name": "Test Model", "description": "pytest created",
                         "sequence_length": 60, "hidden_units": 64, "num_layers": 2,
                         "dropout": 0.2, "learning_rate": 0.001, "batch_size": 32, "epochs": 10},
                   headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert "model_id" in r.json()

def test_update_hyperparams(admin_token):
    r = httpx.put(f"{BASE}/api/v1/lstm/hyperparams",
                  json={"prediction_window_s": 45, "health_threshold": 65,
                        "confidence_threshold": 0.80, "brownout_sensitivity": 0.6},
                  headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert r.json()["success"] is True

def test_user_cannot_access_lstm_control():
    token = httpx.post(f"{BASE}/api/v1/auth/login",
                       json={"email": "marcus@riveralogistics.com", "password": "Rivera@2026"}).json()["access_token"]
    r = httpx.get(f"{BASE}/api/v1/lstm/models",
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
```

---

## SECTION 12 — DEFINITION OF DONE

Run this checklist before marking the implementation complete:

```bash
# 1. Seed all accounts
python scripts/seed_ui_data.py
# Expected: "✓ Seed data inserted successfully" + 9 credentials printed

# 2. Start continuous simulator
docker compose up -d simulator
sleep 60   # let it warm up
# Verify data is flowing
python -c "
from sqlalchemy import create_engine,text
e = create_engine('postgresql://pathwise:pathwise@localhost:5432/pathwise')
with e.connect() as c:
    n = c.execute(text('SELECT COUNT(*) FROM telemetry_live')).scalar()
    print(f'Telemetry rows: {n}')
"
# Expected: > 0 rows

# 3. Run all UI tests
pytest tests/ui/ -v --tb=short
# Expected: all tests PASS

# 4. Build frontend
cd frontend && npm run build
# Expected: no TypeScript errors, build succeeds

# 5. Manual login verification for each account
# Open browser at http://localhost:3000/login and test:
# - admin@pathwise.ai / Admin@PathWise2026  → redirects to /admin/dashboard
# - marcus@riveralogistics.com / Rivera@2026 → redirects to /user/dashboard
# - (repeat for all 8 users)

# 6. Verify route isolation
# While logged in as a user, navigate to /admin/dashboard
# Expected: redirected back to /user/dashboard (not 404, not blank)

# 7. Verify continuous data visible in admin
# Login as admin → Platform Overview → user table shows health scores for all 8 users
# Expected: colored health score in each row, not "–" or "N/A"
```

### Full DoD Checklist

**Accounts:**
- [ ] 9 accounts seeded (1 admin + 8 users) with correct roles
- [ ] All 9 login with their own credentials
- [ ] All passwords bcrypt-hashed in DB
- [ ] Admin redirects to `/admin/dashboard`
- [ ] Users redirect to `/user/dashboard`

**Continuous Data:**
- [ ] Simulator generates ≥1 row/sec per site
- [ ] All 18 user sites have live telemetry
- [ ] Admin can see live health scores for all users

**User Portal (8 pages):**
- [ ] `/user/dashboard` — health scoreboard with user's own sites
- [ ] `/user/sites` — granular per-link analytics
- [ ] `/user/traffic` — traffic distribution + steering events
- [ ] `/user/billing` — plan display, upgrade, invoices
- [ ] `/user/tickets` — raise + track tickets
- [ ] `/user/profile` — view + edit profile
- [ ] All user pages enforce user-only data (no cross-user leakage)

**Admin Portal (6 pages):**
- [ ] `/admin/dashboard` — platform KPIs + all-user health table
- [ ] `/admin/users` — user management with suspend/reactivate
- [ ] `/admin/analytics` — view any user's telemetry
- [ ] `/admin/revenue` — MRR/ARR charts + subscription table
- [ ] `/admin/lstm` — model selector + hyperparameter sliders + retrain
- [ ] `/admin/tickets` — ticket queue with respond functionality

**Security:**
- [ ] User cannot access any `/api/v1/admin/*` endpoint (403)
- [ ] User cannot see another user's telemetry data
- [ ] Admin can access all endpoints
- [ ] JWT verified on every protected endpoint
- [ ] Account lockout after 5 failed login attempts

**Tests:**
- [ ] `test_auth_roles.py` — all 9 logins pass, RBAC enforced
- [ ] `test_billing_api.py` — plans, upgrade, invoices work
- [ ] `test_tickets_api.py` — raise, view, respond flow works
- [ ] `test_continuous_data.py` — all users have live data
- [ ] `test_lstm_control.py` — admin model management works

**UI Quality:**
- [ ] Consistent dark sidebar / light content theme
- [ ] Health score colors match SDD spec: green ≥80, amber 50–79, red <50
- [ ] WebSocket 1 Hz refresh working on user dashboard
- [ ] All Recharts charts have labels and legends
- [ ] Mobile-responsive login page (320px+)
- [ ] Loading states on all data-fetching components
- [ ] Empty states when no data available
- [ ] Toast notifications on all create/update/delete actions

---

*PathWise AI — Team Pathfinders, COSC6370-001*  
*UI Gap Fix Spec — against SRS v1.0 / SDD v1.0 / PVD v1.3*  
*Satisfies: Req-Func-Sw-15 (RBAC), Req-Func-Sw-16 (Auth), Req-Func-Sw-17 (Alerts), Req-Qual-Use-1 (No CLI), SDD §6 (Role-adaptive UI)*
