# DashGrow Multi-Tenant Enterprise Data Portal - Technical Design Spec

**Date:** 2026-08-21  
**Project:** DashGrow Technologies (DG Platform)  
**Status:** Approved  
**Author:** Antigravity AI & DashGrow Core Team  

---

## 1. Overview & Business Vision

The **DashGrow Data Portal** transforms the Enterprise Data Platform into a commercial B2B Multi-Tenant Data-as-a-Service (DaaS) SaaS application. 

### Target Audience & Persona:
1. **DashGrow Platform Owner (Platform Super Admin - You / Bên Bán):**
   - Manages tenant accounts (SMB Client Companies).
   - Monitors cross-tenant data pipelines, BigQuery storage, and `_pipeline_audit_log`.
   - Triggers ingestion jobs, runs dbt transformations and inspects 35 Data Quality test suites.
2. **SMB Business Client (Bên Mua - Shop Owners, F&B/Retail Managers, Factory Directors):**
   - Logs into their dedicated tenant portal (isolated view).
   - Views executive business metrics: Revenue, Orders, P&L, AOV, Delivery Success Rates.
   - Inspects Order Lifecycles via SCD Type 2 Snapshots (`snap_orders`).
   - Receives automated 22:00 P&L sales summaries via Telegram Bot.

---

## 2. Brand Identity & Design System

Following the official **DashGrow Technologies** branding:
- **Backgrounds:** Dark Navy Slate (`#08252a`, `#0a0f1d`) with subtle radial gradients.
- **Accents & Gradients:** `dg-blue` (`#0284c7`), `dg-teal` (`#0d9488`), `dg-green` (`#10b981`).
- **Surface Panels:** Glassmorphism (`rgba(14, 58, 64, 0.45)` with `backdrop-filter: blur(16px)` and `border: 1px solid rgba(255, 255, 255, 0.08)`).
- **Typography:** Google Fonts `Inter` (sans-serif) for UI text and `JetBrains Mono` for IDs and timestamps.

---

## 3. System Architecture

```
                               ┌────────────────────────────────────────────────────────┐
                               │       DASHGROW WEB PORTAL (SPA Client Interface)       │
                               │   • Login / Tenant Workspace Switcher                  │
                               │   • SMB Executive Analytics & Business Intelligence    │
                               │   • SCD 2 Time-Travel Order Inspector                  │
                               │   • DashGrow Admin Pipeline Control Center             │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ (REST JSON + Bearer JWT)
                                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           FASTAPI MULTI-TENANT BACKEND SERVICE                                        │
│                                                                                                                       │
│  [ Core & Security ]      ──> JWT Auth (OAuth2Bearer), Password Hashing (bcrypt), Role/Tenant Middleware              │
│  [ App Database Layer ]   ──> SQLite / PostgreSQL via SQLAlchemy 2.0 (`tenants`, `users`, `audit_events`)            │
│  [ BigQuery Analytics ]   ──> Live queries to `staging` & `marts` datasets (Star Schema + Snapshots)                  │
│  [ Pipeline Controller ]  ──> Executes `main.py` pipelines in background threads & streams status updates             │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema (App Metadata DB)

### `tenants` (SMB Client Organizations)
- `id` (VARCHAR, PK): e.g., `tenant_dg_demo`, `tenant_fnb_chain`
- `name` (VARCHAR): e.g., "Olist Retail Group", "DashGrow Demo Store"
- `plan` (VARCHAR): `starter`, `growth_pro`, `enterprise`
- `created_at` (DATETIME)

### `users` (User Accounts)
- `id` (VARCHAR, PK)
- `tenant_id` (VARCHAR, FK -> `tenants.id`)
- `email` (VARCHAR, UNIQUE)
- `hashed_password` (VARCHAR)
- `full_name` (VARCHAR)
- `role` (VARCHAR): `platform_admin` (DashGrow team) or `client_owner` (SMB client)
- `is_active` (BOOLEAN)

---

## 5. API Endpoints Specification

### Authentication & Tenant
- `POST /api/v1/auth/login`: Authenticate email/password, return JWT token and user profile.
- `GET /api/v1/auth/me`: Get current user info, role, and tenant details.
- `POST /api/v1/auth/seed-demo`: Seed default DashGrow Admin and SMB Client accounts.

### Analytics & BI (Client & Admin)
- `GET /api/v1/analytics/kpis`: Return Total Revenue, Order Count, AOV, Delivery Rate.
- `GET /api/v1/analytics/revenue-trend`: Monthly/Daily revenue timeline data for Chart.js.
- `GET /api/v1/analytics/order-status`: Order status breakdown (Delivered, Shipped, Invoiced).
- `GET /api/v1/analytics/top-categories`: Top 5 revenue-generating product categories.
- `GET /api/v1/analytics/crypto-market`: Real-time market coin metrics from `stg_crypto_market_coins`.

### SCD Type 2 & Observability Explorer
- `GET /api/v1/explorer/scd2/orders`: Search `snap_orders` with complete version history (`valid_from`, `valid_to`, `order_status`).
- `GET /api/v1/explorer/audit-logs`: Fetch recent runs from `_pipeline_audit_log`.
- `GET /api/v1/explorer/quality-tests`: Summary of 35 dbt data tests.

### Pipeline Management (Platform Admin Only)
- `POST /api/v1/pipelines/trigger`: Trigger pipeline (`postgres_db`, `crypto_api`, `all`) with `--full-refresh` flag.
- `GET /api/v1/pipelines/status`: Real-time execution status and logs.

---

## 6. Verification Plan

1. **Backend Verification:**
   - Run PyTest on auth endpoints, JWT generation, and analytics data formats.
   - Verify CORS, tenant filtering, and role-based permissions.
2. **Frontend UI Verification:**
   - Launch FastAPI server locally (`uvicorn src.web.app:app --port 8000`).
   - Test login as `Platform Admin` -> Observe full pipeline control tabs + analytics.
   - Test login as `SMB Client` -> Observe clean business analytics + SCD 2 explorer (pipeline trigger hidden).
   - Test Chart.js interactivity, responsiveness, and dark-glassmorphism theme.
