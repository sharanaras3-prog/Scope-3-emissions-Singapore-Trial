# Marcura — Scope 3 Carbon Intelligence (Streamlit)

A standalone Python/Streamlit version of the Marcura Scope 3 Carbon Intelligence
dashboard, scoped to Singapore operations, with a real satellite map (Esri World
Imagery), multiple-ship tracking (all outbound from Singapore), a live truck
tracker, an emissions calculator, predictive analytics, an AI copilot, and reports.

All data is synthetic and generated in-app — there is no backend or database.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL it prints (usually `http://localhost:8501`).

## Deploy on Streamlit Community Cloud (free)

1. Push this folder to a GitHub repository — make sure `app.py` and
   `requirements.txt` sit at the **root** of the repo (not nested in a subfolder).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, pick your repo and branch.
4. **Main file path**: `app.py`
5. Click **Deploy**. It takes a minute or two to install dependencies and boot.

## Pages

- **Dashboard** — KPIs, emissions trend, source/route breakdowns, network map, AI insights, top suppliers
- **Singapore Map** — full satellite map with toggleable layers (ports, warehouses, vessels, truck routes)
- **Scope 3 Calculator** — interactive emissions estimator
- **Live Vessel Tracking** — vessels outbound from Singapore to global destinations, satellite map + fleet detail
- **Live Truck Tracking** — island-wide road freight, satellite map + fleet detail
- **Predictive Analytics** — 6-month forecast with confidence band
- **AI Carbon Copilot** — chat interface with data-grounded canned responses
- **Reports** — downloadable report cards (illustrative)

## Notes

- The satellite map uses Esri's free World Imagery tile service (no API key needed).
  This requires the deployed app to have normal internet access, which Streamlit
  Community Cloud provides — it will NOT work in network-sandboxed environments.
- The AI Copilot is keyword-matched canned responses, not a live LLM call.
- To regenerate/adjust the synthetic data, edit the `gen_*` functions near the top
  of `app.py` — they're cached with `@st.cache_data` so changes take effect on
  the next full rerun.
