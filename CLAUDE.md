# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app does

Web app for bread and pastry orders at a camping site (Como, Italy). Customers scan a QR code and submit daily orders; managers view, print, and export orders via a password-protected dashboard. Orders are accepted until 18:00 for next-day delivery. UI supports German (default), Italian, and English.

## Running the app

```bash
pip install -r requirements.txt
python app.py
# Runs on http://localhost:8000
```

- Customer form: `/`
- Manager login: `/manager` (default password: `camping2024`, overridable via `MANAGER_PWD` env var)

**Production:**
```bash
gunicorn -w 2 -b 0.0.0.0:80 app:app
```

**Generate QR code:**
```bash
python generate_qr.py http://your-domain.com
```

## Architecture

Single-file Flask app (`app.py`, ~206 lines). No frontend framework — all CSS and JS are inlined in Jinja2 templates under `templates/`. SQLite database (`orders.db`) is auto-created on first run via `init_db()`.

**Key config constants in `app.py` (lines 16–29):**
- `MANAGER_PASSWORD` — reads from `MANAGER_PWD` env var, fallback `camping2024`
- `CUTOFF_HOUR = 18` — orders blocked server-side after 18:00
- `PRODUCTS` dict — product names and prices (EUR); this is the source of truth for both form rendering and server-side total recalculation

**Routes:**
- `GET /` — order form
- `POST /submit` — validates cutoff, recalculates total server-side, inserts into DB
- `GET/POST /manager` — login form
- `GET /manager/dashboard` — orders table filtered by delivery date
- `GET /manager/export` — CSV download (semicolon-delimited, UTF-8)
- `GET /manager/logout` — clears session

**Delivery date logic:** `delivery_date_for()` returns tomorrow's date; `is_past_cutoff()` checks against `CUTOFF_HOUR`. Both are used server-side on `/submit` and client-side via JS in `order.html`.

**Translations:** All three languages are embedded as `data-de`, `data-it`, `data-en` HTML attributes directly in the templates. `localStorage` persists the selected language. No i18n library.

**Database schema** (single `orders` table): `id`, `created_at`, `delivery_date`, `customer_name`, `pitch_number`, one INTEGER column per product, `total_amount`.

## Dependencies

- `flask>=3.0`
- `qrcode[pil]>=7.4`
