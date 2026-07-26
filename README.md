# Marcura — Scope 3 Carbon Intelligence (Streamlit)

A standalone Python/Streamlit version of the Marcura Scope 3 Carbon Intelligence
dashboard, scoped to Singapore operations: real satellite/Google Maps views,
multiple-ship tracking (all outbound from Singapore, with live AIS option),
estimated fuel consumption, an AI executive summary agent, a dashboard-grounded
AI chatbot, predictive analytics, and reports.

Core dashboard data is synthetic (regenerated each session) — there is no
backend database. Two features can optionally connect to real live services if
you provide free API keys (see below); without keys, everything still works
using data-grounded fallbacks.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL it prints (usually `http://localhost:8501`).

## Deploy on Streamlit Community Cloud (free)

1. Push `app.py`, `requirements.txt`, and this `README.md` to a GitHub
   repository — all three sitting at the **root** of the repo (not nested in
   a subfolder).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, pick your repo and branch.
4. **Main file path**: `app.py`
5. Click **Deploy**. It takes a minute or two to install dependencies and boot.

## Scope 3 Calculator & AI Predictions \u2014 per vessel, per truck, per buyer/seller

Every vessel and truck now has its own dedicated Scope 3 breakdown, not just a
fleet-wide average:

- **Per-vessel** (click any vessel on the Global Fleet View map): fuel-based
  emissions estimate (cube-law from speed) **and** a GLEC distance-based
  cross-check (cargo weight \u00d7 remaining distance \u00d7 intensity factor),
  cargo weight/DWT, buyer, seller, an **AI Summary** of the voyage, and a
  separate **AI Prediction** (30-day forward-looking emissions trend)
- **Per-truck** (Live Truck Tracking \u2192 select any truck from the dropdown):
  the same GLEC distance-based calculation, buyer/seller, AI summary, and AI
  prediction
- **Per-seller** (Companies page) and **per-buyer** (Buyers page): select any
  company to see its emissions profile and generate an AI prediction for the
  next quarter
- **Company-wide** (Dashboard): an AI Executive Summary plus a separate
  AI Prediction covering the whole fleet and supplier base

All AI features use real Claude if you add a free Anthropic API key in the
sidebar; without one, they fall back to a data-grounded rule-based engine that
still reads live numbers out of the actual dataframes (not hardcoded text).

## Navigation

The sidebar mirrors MarineTraffic's menu structure, grouped into three sections:

**Marine Traffic** (matches the reference product's menu)
- **Map** \u2192 Global Fleet View (the main interactive vessel map)
- **Vessels** \u2192 Live Vessel Tracking
- **Ports** \u2192 real port directory with map
- **Lighthouses**, **Stations** \u2014 placeholder pages (out of scope for this prototype, clearly labeled)
- **Companies** \u2192 supplier/operator list with emissions data
- **Photo gallery** \u2192 the vessel-class illustrations used throughout the app
- **Maritime news** \u2014 illustrative sample headlines (not a live feed)

**Account**
- **Fleet dashboard** \u2192 the main KPI/emissions Dashboard
- **Containers** \u2014 illustrative container-type mix
- **Plans & Pricing** \u2014 illustrative mockup tiers
- **Data services** \u2192 Reports page
- **Notifications** \u2192 AI-flagged alerts feed

**Scope 3 Intelligence** (this app's actual core functionality)
- Scope 3 Calculator, Live Truck Tracking, Predictive Analytics, AI Carbon Copilot, Google Maps / Earth View

A "Log in / create account" button appears at the bottom of the sidebar for visual
parity with the reference product \u2014 it's illustrative only, no real auth.

## Pages

- **Dashboard** — KPIs, emissions trend, source/route breakdowns, network map,
  **AI Executive Summary** (button), AI insights, top suppliers
- **Global Fleet View** — MarineTraffic-style dense global map: ~3,100 synthetic
  vessels color-coded by class (cargo/tanker/fishing/passenger/high-speed/
  pleasure) with heading arrows, clustered along the world's real major
  shipping lanes (trans-Pacific, trans-Atlantic, Suez, Malacca, Panama, etc.).
  **Click any vessel** to open a MarineTraffic-style detail card: representative
  vessel-class illustration, flag, route with real port codes, ATD/ETA, a
  voyage-progress slider, past-track and route-forecast mini-maps, navigational
  status, speed/course/draught, **estimated Scope 3 emissions** for that
  specific vessel, **live weather** at its current position (Open-Meteo, real
  data), and an **AI-generated summary** of the vessel's voyage and footprint
- **Google Maps / Earth View** — one-click Google Earth Web link (no key needed),
  plus a Google Maps satellite view with port/vessel markers if you supply a
  free Google Maps Static API key
- **Scope 3 Calculator** — interactive emissions estimator
- **Live Vessel Tracking** — multiple ships outbound from Singapore to global
  destinations, with **estimated fuel consumption and CO2 rate** per vessel
  (cube-law model from speed). Toggle to **Live AIS** mode to pull real,
  live ship positions near Singapore from AISStream.io (free API key)
- **Live Truck Tracking** — island-wide road freight
- **Predictive Analytics** — 6-month forecast with confidence band
- **AI Carbon Copilot** — chatbot that can answer about any vessel, truck,
  supplier, route, or forecast on the dashboard by name; uses real Claude
  (Anthropic API) if you add a key in the sidebar, otherwise a data-grounded
  rule-based engine
- **Reports** — downloadable report cards (illustrative)

## Optional free API keys (sidebar / per-page)

| Feature | Provider | Where to get a key | Cost |
|---|---|---|---|
| AI Executive Summary + Chatbot | Anthropic | console.anthropic.com | Pay-as-you-go, cheap for this use |
| Live AIS ship tracking | AISStream.io | aisstream.io | Free |
| Google Maps satellite markers | Google Cloud (Maps Static API) | console.cloud.google.com | Free tier available |

All keys are entered as password-type fields, kept only in the browser session,
and never written to disk or logs.

## Notes on "live" data honesty

- **Weather data in the vessel detail panel is genuinely live** \u2014 pulled from
  Open-Meteo (free, no API key needed) for the vessel's exact current position,
  every time you open a vessel's detail panel.
- **The Global Fleet View is synthetic, not a live 300K-vessel feed.** There is
  no free public data source with that scale/density of live global AIS
  positions — that's MarineTraffic/Kpler's own paid commercial network. This
  page generates a large, realistically-distributed synthetic fleet along the
  world's actual major shipping lanes, in the same visual language (colored,
  direction-arrow markers), so the concept can be demoed convincingly. It's
  labeled as synthetic directly in the page.
- **Fuel consumption is always an estimate.** Neither AIS nor any free public
  feed transmits real fuel-flow data for arbitrary vessels. This app estimates
  it from speed using the standard naval-architecture cube law (fuel burn
  scales roughly with speed³ relative to a vessel's design service speed),
  which is the same approximation GLEC/IMO-style tools use when direct fuel
  data isn't available. It's clearly labeled as an estimate in the UI.
- **Live AIS mode** requires a real internet connection with access to
  `stream.aisstream.io` — this works on Streamlit Community Cloud but will
  fail in network-sandboxed environments.
- **The AI agent** (summary + chatbot) only calls a real LLM if you provide
  your own Anthropic API key. Without one, it uses a rule-based engine that
  still reads live numbers out of the current dataframes rather than
  hardcoded text — so answers stay accurate even without a live LLM call.
- To regenerate/adjust the synthetic data, edit the `gen_*` functions near the
  top of `app.py` — they're cached with `@st.cache_data`.
