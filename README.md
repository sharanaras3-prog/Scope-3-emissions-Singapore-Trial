# Marcura — Scope 3 Carbon Intelligence (Streamlit)

A simple, single-file Streamlit dashboard for Singapore maritime logistics
Scope 3 carbon intelligence. All data is synthetic — there is no backend.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL it prints (usually `http://localhost:8501`).

## Deploy on Streamlit Community Cloud (free)

1. Push `app.py` and `requirements.txt` to a GitHub repo (both at the root,
   not inside a subfolder).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Click **New app**, pick your repo, set **Main file path** to `app.py`.
4. Click **Deploy**.

## Pages

- **Dashboard** — KPIs, emissions trend, source/route breakdown, Singapore map, AI insights, top suppliers
- **Singapore Map** — satellite map (real Esri imagery) with toggleable layers
- **Scope 3 Calculator** — interactive emissions estimator
- **Live Vessel Tracking** — vessels outbound from Singapore
- **Live Truck Tracking** — island-wide road freight
- **Predictive Analytics** — 6-month forecast
- **AI Carbon Copilot** — simple rule-based chat, grounded in the synthetic data
- **Reports** — downloadable report cards (illustrative)

## Notes

- The satellite map uses Esri's free World Imagery tiles (no API key needed).
- The AI Copilot uses keyword-matched canned responses, not a live LLM call.
- To adjust the data, edit the `gen_*` functions near the top of `app.py`.
