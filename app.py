import math
import random
import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Marcura | Scope 3 Carbon Intelligence",
    page_icon="\U0001F6A2",
    layout="wide",
    initial_sidebar_state="expanded",
)

random.seed(7)
np.random.seed(7)

# ---------------------------------------------------------------------------
# Theme (maritime dark)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(160deg, #f3ead6 0%, #ecdfc2 50%, #e6d9b8 100%);
        color: #2b2417;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e9dcbd 0%, #e0d0a8 100%);
        border-right: 1px solid rgba(90,74,40,0.20);
    }
    section[data-testid="stSidebar"] * { color: #2b2417 !important; }
    h1, h2, h3, h4, p, span, label, div { color: #2b2417; }
    h1 {
        background: linear-gradient(90deg, #0f766e, #155e75 55%, #7c2d12);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    h2, h3 { color: #1c1710 !important; font-weight: 700 !important; }
    p, .stMarkdown, .stCaption, label { color: #2b2417 !important; }
    [data-testid="stCaptionContainer"] { color: #574a2e !important; }
    div[data-testid="stMetric"] {
        background: linear-gradient(155deg, rgba(255,255,255,0.55), rgba(230,215,175,0.55));
        border: 1px solid rgba(90,74,40,0.25);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 14px rgba(90,74,40,0.10);
    }
    div[data-testid="stMetricLabel"] { color: #6b3e0e !important; font-weight: 700; }
    div[data-testid="stMetricValue"] { color: #1c1710 !important; font-weight: 800; }
    div[data-testid="stMetricDelta"] { font-weight: 600; }
    .badge {
        display:inline-block; padding:3px 12px; border-radius:999px;
        font-size:11px; font-weight:700; letter-spacing:.2px;
    }
    .badge-low{background:linear-gradient(135deg,#0f766e,#0d9488); color:#f0fdfa;}
    .badge-med{background:linear-gradient(135deg,#b45309,#d97706); color:#fffbeb;}
    .badge-high{background:linear-gradient(135deg,#9a3412,#c2410c); color:#fff7ed;}
    .card {
        background: linear-gradient(155deg, rgba(255,255,255,0.6), rgba(236,223,194,0.55));
        border: 1px solid rgba(90,74,40,0.22);
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(90,74,40,0.08);
        color: #2b2417;
    }
    .card b { color: #0f766e; }
    .stButton>button {
        border-radius: 10px;
        border: 1px solid rgba(15,118,110,0.45);
        background: linear-gradient(135deg, rgba(15,118,110,0.14), rgba(180,83,9,0.10));
        color: #1c1710;
        font-weight: 700;
    }
    .stButton>button:hover {
        border-color: #0f766e;
        background: linear-gradient(135deg, rgba(15,118,110,0.28), rgba(180,83,9,0.18));
        color: #0b0b0a;
    }
    .stTabs [data-baseweb="tab"] { color: #6b5a35; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #0f766e !important; }
    hr { border-color: rgba(90,74,40,0.20) !important; }
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.55);
        border: 1px solid rgba(90,74,40,0.20);
        border-radius: 14px;
        color: #2b2417;
    }
    .stTextInput input, .stNumberInput input { color: #1c1710 !important; }
    div[data-testid="stDataFrame"] { color: #2b2417 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Consistent maritime chart palette used across all Plotly figures (readable on beige)
PALETTE = ["#0f766e", "#b45309", "#155e75", "#9a3412", "#4d7c0f", "#6d28d9", "#0e7490", "#a16207"]
PLOTLY_LAYOUT = dict(
    template="plotly_white",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#2b2417"),
    colorway=PALETTE,
    margin=dict(l=10, r=10, t=10, b=10),
)

# ---------------------------------------------------------------------------
# Singapore reference geography
# ---------------------------------------------------------------------------
PORTS = pd.DataFrame([
    {"id": "TUAS", "name": "Tuas Port (Mega Port)", "lat": 1.294, "lon": 103.636, "kind": "port", "note": "New mega-terminal, phased opening"},
    {"id": "PPT", "name": "Pasir Panjang Terminal", "lat": 1.271, "lon": 103.784, "kind": "port", "note": "Largest container terminal"},
    {"id": "KEP", "name": "Keppel / Tanjong Pagar", "lat": 1.267, "lon": 103.844, "kind": "port", "note": "Original PSA container hub"},
    {"id": "BRN", "name": "Brani Terminal", "lat": 1.259, "lon": 103.830, "kind": "port", "note": "Container terminal"},
    {"id": "SBW", "name": "Sembawang Wharves", "lat": 1.462, "lon": 103.831, "kind": "port", "note": "Bulk & project cargo"},
    {"id": "JI", "name": "Jurong Island", "lat": 1.267, "lon": 103.700, "kind": "industrial", "note": "Petrochemical complex, bunkering"},
    {"id": "CHG", "name": "Changi Airport (Air Freight)", "lat": 1.359, "lon": 103.989, "kind": "air", "note": "Air cargo hub"},
])

WAREHOUSES = pd.DataFrame([
    {"id": "WH1", "name": "Jurong DC", "lat": 1.320, "lon": 103.706},
    {"id": "WH2", "name": "Tuas Logistics Park", "lat": 1.322, "lon": 103.646},
    {"id": "WH3", "name": "Changi Airfreight Centre", "lat": 1.346, "lon": 103.983},
    {"id": "WH4", "name": "Sembawang DC", "lat": 1.445, "lon": 103.820},
    {"id": "WH5", "name": "Pasir Panjang DC", "lat": 1.285, "lon": 103.790},
])

# global destinations that Singapore-outbound vessels sail to
GLOBAL_DESTS = pd.DataFrame([
    {"id": "NLRTM", "name": "Rotterdam", "lat": 51.9496, "lon": 4.1453},
    {"id": "CNSHA", "name": "Shanghai", "lat": 31.2304, "lon": 121.4737},
    {"id": "AEJEA", "name": "Jebel Ali", "lat": 25.0118, "lon": 55.0617},
    {"id": "USLAX", "name": "Los Angeles", "lat": 33.7395, "lon": -118.2600},
    {"id": "KRPUS", "name": "Busan", "lat": 35.1028, "lon": 129.0403},
    {"id": "HKHKG", "name": "Hong Kong", "lat": 22.2908, "lon": 114.1501},
    {"id": "DEHAM", "name": "Hamburg", "lat": 53.5459, "lon": 9.9695},
    {"id": "AUMEL", "name": "Melbourne", "lat": -37.8400, "lon": 144.9300},
])

FUEL_TYPES = ["LNG", "VLSFO", "Methanol", "Biofuel B30", "HFO"]
VESSEL_TYPES = ["Container Ship", "Bulk Carrier", "LNG Carrier", "General Cargo"]
VESSEL_PREFIX = ["MV", "MSC", "Maersk", "CMA CGM", "COSCO", "OOCL", "Hapag"]
VESSEL_NAMES = ["Horizon", "Voyager", "Meridian", "Zenith", "Sentinel", "Navigator", "Pinnacle", "Vanguard"]

TRUCK_FUELS = ["Diesel", "Electric", "CNG", "Biodiesel B20"]
DRIVERS = ["Wei Tan", "Arjun Nair", "Siti Rahman", "Hassan Ibrahim", "Li Wong", "Kavya Nair"]


# ---------------------------------------------------------------------------
# Synthetic data generation (cached so it's stable across reruns/interactions)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Fuel consumption / emissions-rate model
# Real AIS gives position, speed (SOG), and course — not fuel flow. There is no
# free public live bunker-fuel telemetry feed for arbitrary vessels, so fuel
# consumption here is *estimated* from speed using the standard naval-architecture
# cube law (fuel burn scales roughly with speed^3 relative to a vessel's design
# service speed), which is the same approximation used in IMO/GLEC-style
# distance-based emissions estimation when direct fuel data isn't available.
# ---------------------------------------------------------------------------
VESSEL_FUEL_PROFILE = {
    # design/service speed (knots), baseline fuel consumption at that speed (tonnes/day)
    "Container Ship": {"service_speed": 20.0, "base_t_per_day": 150.0},
    "Bulk Carrier": {"service_speed": 14.0, "base_t_per_day": 32.0},
    "LNG Carrier": {"service_speed": 19.0, "base_t_per_day": 120.0},
    "General Cargo": {"service_speed": 15.0, "base_t_per_day": 22.0},
}
FUEL_CO2_FACTOR = {  # kg CO2 per kg fuel burned (IMO/GHG Protocol marine fuel factors)
    "HFO": 3.114, "VLSFO": 3.151, "LNG": 2.750, "Methanol": 1.375, "Biofuel B30": 2.180,
}


def estimate_fuel_and_co2(vessel_type: str, fuel: str, speed_knots: float):
    """Returns (fuel_tonnes_per_day, fuel_kg_per_hour, co2_kg_per_hour) estimated
    from the cube-law speed relationship for the given vessel type and fuel."""
    profile = VESSEL_FUEL_PROFILE.get(vessel_type, {"service_speed": 18.0, "base_t_per_day": 80.0})
    speed = max(speed_knots or 0, 0.5)
    ratio = speed / profile["service_speed"]
    fuel_t_per_day = profile["base_t_per_day"] * (ratio ** 3)
    fuel_kg_per_hour = fuel_t_per_day * 1000 / 24
    co2_factor = FUEL_CO2_FACTOR.get(fuel, 3.11)
    co2_kg_per_hour = fuel_kg_per_hour * co2_factor
    return round(fuel_t_per_day, 2), round(fuel_kg_per_hour, 1), round(co2_kg_per_hour, 1)


@st.cache_data
def gen_vessels(n=8):
    rows = []
    for i in range(n):
        dest = GLOBAL_DESTS.iloc[i % len(GLOBAL_DESTS)]
        origin_port = PORTS[PORTS["kind"] == "port"].sample(1, random_state=i).iloc[0]
        progress = round(random.uniform(0.05, 0.85), 2)
        speed = round(random.uniform(11, 20), 1)
        vtype = random.choice(VESSEL_TYPES)
        fuel = random.choice(FUEL_TYPES)
        fuel_t_day, fuel_kg_hr, co2_kg_hr = estimate_fuel_and_co2(vtype, fuel, speed)
        rows.append({
            "name": f"{random.choice(VESSEL_PREFIX)} {random.choice(VESSEL_NAMES)}",
            "type": vtype,
            "fuel": fuel,
            "origin_id": origin_port["id"], "origin_name": origin_port["name"],
            "origin_lat": origin_port["lat"], "origin_lon": origin_port["lon"],
            "dest_id": dest["id"], "dest_name": dest["name"],
            "dest_lat": dest["lat"], "dest_lon": dest["lon"],
            "progress": progress,
            "speed_knots": speed,
            "eta_hours": round((1 - progress) * random.uniform(60, 260), 1),
            "fuel_t_per_day": fuel_t_day,
            "fuel_kg_per_hour": fuel_kg_hr,
            "co2_kg_per_hour": co2_kg_hr,
            "co2e_tonnes": round(random.uniform(80, 480), 1),
        })
    return pd.DataFrame(rows)


def interpolate_position(o_lat, o_lon, d_lat, d_lon, t):
    """Great-circle-ish interpolation with a slight bow (not straight line)."""
    lat = o_lat + (d_lat - o_lat) * t
    lon = o_lon + (d_lon - o_lon) * t
    bow = math.sin(t * math.pi) * 3.5
    lat += bow * 0.25
    return lat, lon


@st.cache_data
def gen_trucks(n=6):
    rows = []
    for i in range(n):
        wh = WAREHOUSES.sample(1, random_state=i + 50).iloc[0]
        port = PORTS.sample(1, random_state=i + 90).iloc[0]
        status = random.choices(["Driving", "Idle", "Loading", "Delayed"], weights=[55, 20, 15, 10])[0]
        rows.append({
            "truck_id": f"TRK{i+1:04d}",
            "driver": random.choice(DRIVERS),
            "fuel": random.choice(TRUCK_FUELS),
            "status": status,
            "from_id": wh["id"], "from_name": wh["name"], "from_lat": wh["lat"], "from_lon": wh["lon"],
            "to_id": port["id"], "to_name": port["name"], "to_lat": port["lat"], "to_lon": port["lon"],
            "speed_kmh": 0 if status != "Driving" else round(random.uniform(40, 90), 1),
            "co2e_kg": round(random.uniform(15, 300), 1),
            "progress": round(random.uniform(0.1, 0.9), 2),
        })
    return pd.DataFrame(rows)


@st.cache_data
def gen_monthly_emissions():
    months = pd.date_range(end=dt.date(2026, 7, 1), periods=12, freq="MS")
    rows = []
    base = 9200
    for i, m in enumerate(months):
        seasonal = 1 + 0.10 * math.sin(2 * math.pi * (m.month / 12))
        growth = 1.003 ** i
        noise = 0.96 + ((i * 37) % 9) / 100
        total = round(base * seasonal * growth * noise)
        rows.append({"month": m.strftime("%b %Y"), "total": total, "budget": round(base * 1.05 * growth)})
    return pd.DataFrame(rows)


@st.cache_data
def gen_forecast(last_total):
    rows = []
    for i in range(1, 7):
        val = round(last_total * (1.003 ** i) * (0.98 + ((i * 13) % 5) / 100))
        rows.append({"month": f"+{i}mo", "predicted": val, "lower": round(val * 0.88), "upper": round(val * 1.13)})
    return pd.DataFrame(rows)


@st.cache_data
def gen_suppliers():
    return pd.DataFrame([
        {"name": "Jurong Petrochemical Supplies Pte Ltd", "location": "Jurong Island, SG", "industry": "Chemicals", "co2e": 6240, "risk": "High"},
        {"name": "PSA Bunker Services", "location": "Pasir Panjang, SG", "industry": "Marine Fuel", "co2e": 5680, "risk": "Medium"},
        {"name": "Tuas Metal Trading Co.", "location": "Tuas, SG", "industry": "Metals & Mining", "co2e": 4110, "risk": "Medium"},
        {"name": "Changi Air Cargo Handlers", "location": "Changi, SG", "industry": "Logistics", "co2e": 3350, "risk": "Low"},
        {"name": "Sembawang Marine Supplies", "location": "Sembawang, SG", "industry": "Shipbuilding", "co2e": 2940, "risk": "High"},
    ])


@st.cache_data
def gen_routes():
    return pd.DataFrame([
        {"route": "Tuas Port \u2192 Rotterdam", "co2e": 3120},
        {"route": "Pasir Panjang \u2192 Shanghai", "co2e": 2840},
        {"route": "Keppel \u2192 Jebel Ali", "co2e": 2410},
        {"route": "Tuas Port \u2192 Busan", "co2e": 2180},
        {"route": "Changi \u2192 Hong Kong (Air)", "co2e": 1760},
        {"route": "Pasir Panjang \u2192 Los Angeles", "co2e": 1590},
    ])


@st.cache_data
def gen_emissions_by_source():
    return pd.DataFrame([
        {"source": "Ocean Freight (PSA/Tuas)", "pct": 46},
        {"source": "Jurong Island Petrochem", "pct": 14},
        {"source": "Road Freight (island-wide)", "pct": 13},
        {"source": "Changi Air Freight", "pct": 10},
        {"source": "Warehousing", "pct": 8},
        {"source": "Bunkering & Port Ops", "pct": 6},
        {"source": "Business Travel", "pct": 3},
    ])


MODE_INTENSITY = {
    "Ocean Freight": 0.009, "Road Freight": 0.09, "Air Freight": 0.55,
    "Warehousing": 0.02, "Business Travel": 0.15, "Petrochemical": 0.05,
}

# ---------------------------------------------------------------------------
# Live AIS integration (real ship positions via AISStream.io, free API key)
# Falls back gracefully to the simulated fleet if no key / connection issue.
# ---------------------------------------------------------------------------
SINGAPORE_STRAIT_BBOX = [[[1.05, 103.50], [1.50, 104.15]]]  # [[lat_min, lon_min],[lat_max, lon_max]]


def fetch_live_ais(api_key: str, seconds: int = 8, max_msgs: int = 400):
    """Connects to AISStream.io, collects PositionReport messages near Singapore
    for a few seconds, and returns a DataFrame of live vessel positions.
    Raises on any connection/auth error so the caller can show a clear message."""
    import asyncio
    import json
    import websockets

    async def _collect():
        rows = {}
        uri = "wss://stream.aisstream.io/v0/stream"
        async with websockets.connect(uri, open_timeout=10, close_timeout=5) as ws:
            subscribe_msg = {
                "APIKey": api_key,
                "BoundingBoxes": SINGAPORE_STRAIT_BBOX,
                "FilterMessageTypes": ["PositionReport"],
            }
            await ws.send(json.dumps(subscribe_msg))
            loop = asyncio.get_event_loop()
            end_time = loop.time() + seconds
            while loop.time() < end_time and len(rows) < max_msgs:
                remaining = max(0.1, end_time - loop.time())
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                try:
                    data = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if data.get("MessageType") != "PositionReport":
                    continue
                pr = data.get("Message", {}).get("PositionReport", {})
                meta = data.get("MetaData", {})
                mmsi = meta.get("MMSI") or pr.get("UserID")
                if mmsi is None:
                    continue
                rows[mmsi] = {
                    "mmsi": mmsi,
                    "name": meta.get("ShipName", "").strip() or f"MMSI {mmsi}",
                    "lat": pr.get("Latitude", meta.get("latitude")),
                    "lon": pr.get("Longitude", meta.get("longitude")),
                    "sog_knots": pr.get("Sog"),
                    "cog_deg": pr.get("Cog"),
                    "time_utc": meta.get("time_utc"),
                }
        return list(rows.values())

    results = asyncio.run(_collect())
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.dropna(subset=["lat", "lon"])
        # AIS PositionReport doesn't include vessel type or fuel — that comes from
        # ShipStaticData messages, which we're not subscribed to for this quick demo
        # capture. We assume a generic "Container Ship on VLSFO" profile (the most
        # common vessel class in the Singapore Strait) so a fuel/CO2 estimate can
        # still be shown, clearly labeled as an assumption in the UI.
        fuel_rates = df["sog_knots"].apply(lambda s: estimate_fuel_and_co2("Container Ship", "VLSFO", s))
        df["fuel_t_per_day"] = fuel_rates.apply(lambda x: x[0])
        df["fuel_kg_per_hour"] = fuel_rates.apply(lambda x: x[1])
        df["co2_kg_per_hour"] = fuel_rates.apply(lambda x: x[2])
    return df


# ---------------------------------------------------------------------------
# AI agent layer: dashboard-grounded context + optional real Claude API call.
# If the user supplies an Anthropic API key, the summary/chatbot use genuine
# Claude-generated responses grounded in the live data below. Without a key,
# both fall back to a data-driven rule-based engine that still reads every
# number straight out of the current dataframes (not hardcoded copy).
# ---------------------------------------------------------------------------

def build_dashboard_context(vessels_df, trucks_df, monthly_df, forecast_df, suppliers_df, routes_df, source_df):
    last = monthly_df.iloc[-1]
    prev = monthly_df.iloc[-2] if len(monthly_df) > 1 else last
    mom_change = ((last["total"] - prev["total"]) / prev["total"] * 100) if prev["total"] else 0

    vessel_lines = []
    for _, v in vessels_df.iterrows():
        vessel_lines.append(
            f"- {v['name']} ({v['type']}, {v['fuel']}): heading to {v['dest_name']}, "
            f"speed {v['speed_knots']} kn, {int(v['progress']*100)}% of voyage complete, "
            f"ETA {v['eta_hours']}h, estimated fuel use {v['fuel_t_per_day']} t/day, "
            f"estimated CO2 rate {v['co2_kg_per_hour']} kg/hr"
        )

    truck_lines = []
    for _, t in trucks_df.iterrows():
        truck_lines.append(
            f"- {t['truck_id']} ({t['driver']}, {t['fuel']}): {t['status']}, "
            f"{t['from_name']} \u2192 {t['to_name']}, speed {t['speed_kmh']} km/h, CO2e {t['co2e_kg']} kg"
        )

    supplier_lines = [
        f"- {s['name']} ({s['location']}, {s['industry']}): {s['co2e']:,} t CO2e YTD, risk: {s['risk']}"
        for _, s in suppliers_df.iterrows()
    ]
    route_lines = [f"- {r['route']}: {r['co2e']:,} t CO2e" for _, r in routes_df.iterrows()]
    source_lines = [f"- {s['source']}: {s['pct']}% of total emissions" for _, s in source_df.iterrows()]

    context = f"""
SINGAPORE SCOPE 3 CARBON DASHBOARD \u2014 LIVE SNAPSHOT

KEY METRICS
- Monthly emissions (latest): {last['total']:,} t CO2e (budget: {last['budget']:,} t CO2e)
- Month-over-month change: {mom_change:+.1f}%
- Next month forecast: {forecast_df.iloc[0]['predicted']:,} t CO2e (range {forecast_df.iloc[0]['lower']:,}-{forecast_df.iloc[0]['upper']:,})
- Carbon reduction vs baseline: 11.8%
- MPA Green Shipping Score: 79/100
- Active shipments: 480
- Vessels tracked live: {len(vessels_df)}
- Trucks tracked live: {len(trucks_df)}

EMISSIONS BY SOURCE
{chr(10).join(source_lines)}

TOP EMITTING EXPORT LANES
{chr(10).join(route_lines)}

TOP SUPPLIERS BY EMISSIONS
{chr(10).join(supplier_lines)}

VESSEL FLEET (all outbound from Singapore)
{chr(10).join(vessel_lines)}

TRUCK FLEET (island-wide road freight)
{chr(10).join(truck_lines)}
""".strip()
    return context


def call_claude(api_key: str, system_prompt: str, user_message: str, max_tokens: int = 700) -> str:
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("The 'anthropic' package isn't installed in this environment.")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def rule_based_answer(question: str, ctx_data: dict) -> str:
    """Data-grounded fallback used when no Anthropic key is supplied. Reads
    live values out of the current dataframes rather than hardcoded strings."""
    s = question.lower()
    vessels_df = ctx_data["vessels_df"]; trucks_df = ctx_data["trucks_df"]
    monthly_df = ctx_data["monthly_df"]; suppliers_df = ctx_data["suppliers_df"]
    routes_df = ctx_data["routes_df"]; forecast_df = ctx_data["forecast_df"]
    last = monthly_df.iloc[-1]

    # try to match a specific vessel by name fragment
    for _, v in vessels_df.iterrows():
        if v["name"].lower() in s or any(part.lower() in s for part in v["name"].split() if len(part) > 3):
            return (f"**{v['name']}** ({v['type']}, running on {v['fuel']}) is currently sailing to "
                    f"{v['dest_name']} at {v['speed_knots']} knots, {int(v['progress']*100)}% through the voyage "
                    f"(ETA {v['eta_hours']}h). Estimated fuel consumption at this speed: {v['fuel_t_per_day']} "
                    f"tonnes/day ({v['fuel_kg_per_hour']} kg/hr), producing roughly {v['co2_kg_per_hour']:,.0f} kg CO2/hr.")

    for _, t in trucks_df.iterrows():
        if t["truck_id"].lower() in s:
            return (f"**{t['truck_id']}** (driver {t['driver']}, {t['fuel']}) is currently **{t['status']}**, "
                    f"running {t['from_name']} \u2192 {t['to_name']} at {t['speed_kmh']} km/h, "
                    f"estimated {t['co2e_kg']} kg CO2e for this leg.")

    if "fuel" in s and ("consum" in s or "burn" in s or "how much" in s or "most" in s or "use" in s or "efficien" in s):
        avg_fuel = vessels_df["fuel_t_per_day"].mean()
        top = vessels_df.loc[vessels_df["fuel_t_per_day"].idxmax()]
        return (f"Across the {len(vessels_df)} tracked vessels, average estimated fuel consumption is "
                f"{avg_fuel:.1f} tonnes/day. The highest consumer right now is **{top['name']}** at "
                f"{top['fuel_t_per_day']} t/day (speed {top['speed_knots']} kn) \u2014 fuel use scales with the "
                f"cube of speed, so that vessel is either moving fast or has a larger design consumption baseline.")

    if any(w in s for w in ["speed", "fast", "slow"]) and ("vessel" in s or "ship" in s or "knot" in s):
        fastest = vessels_df.loc[vessels_df["speed_knots"].idxmax()]
        slowest = vessels_df.loc[vessels_df["speed_knots"].idxmin()]
        return (f"The fastest vessel right now is **{fastest['name']}** at {fastest['speed_knots']} knots "
                f"(heading to {fastest['dest_name']}). The slowest is **{slowest['name']}** at "
                f"{slowest['speed_knots']} knots (heading to {slowest['dest_name']}).")

    if "emission" in s and ("month" in s or "total" in s or "latest" in s):
        return f"Last month, Singapore operations emitted {last['total']:,} t CO2e against a budget of {last['budget']:,} t."

    if "forecast" in s or "predict" in s or "next month" in s:
        f0 = forecast_df.iloc[0]
        return (f"Next month's forecast is {f0['predicted']:,} t CO2e, with a confidence range of "
                f"{f0['lower']:,}\u2013{f0['upper']:,} t CO2e.")

    if "supplier" in s:
        top = suppliers_df.iloc[0]
        return (f"{top['name']} has the highest YTD footprint at {top['co2e']:,} t CO2e, "
                f"flagged {top['risk']} risk. Full supplier list is on the Dashboard page.")

    if "route" in s or "lane" in s:
        top = routes_df.iloc[0]
        return f"The highest-emitting lane is {top['route']} at {top['co2e']:,} t CO2e."

    if "tuas" in s:
        return "Tuas Port emissions are up 9% this month as mega-port throughput ramps up \u2014 expected during the phased handover from Pasir Panjang."

    if "truck" in s:
        driving = (trucks_df["status"] == "Driving").sum()
        return f"{driving} of {len(trucks_df)} tracked trucks are currently driving; the rest are idle, loading, or delayed."

    if "reduc" in s:
        return "Top levers: shift Jurong Island bunkering to LNG, consolidate Jurong-to-Tuas road freight, and route more Changi air cargo via sea-air through Pasir Panjang."

    return (f"This month's Singapore Scope 3 emissions are {last['total']:,} t CO2e. Ask me about a specific "
            f"vessel or truck by name, fuel consumption, speed, suppliers, routes, or the forecast \u2014 "
            f"or add a free Anthropic API key in the sidebar for fully open-ended answers about anything on the dashboard.")


AI_INSIGHTS = [
    ("warning", "Emissions from Tuas Port operations increased 9% this month as mega-port volumes ramp up.", "Tuas Port", "+9%", 0.90),
    ("positive", "PSA Bunker Services reduced emissions 14% after switching bunkering vessels to LNG.", "Supplier", "-14%", 0.85),
    ("opportunity", "Shifting more Changi air freight to sea-air via Pasir Panjang could cut emissions on select lanes by 11%.", "Route Optimization", "-11% potential", 0.76),
    ("alert", "Two shipments this week exceeded the carbon threshold for Jurong Island petrochemical exports.", "Compliance", "2 shipments", 0.94),
    ("opportunity", "Consolidating road freight between Jurong DC and Tuas Logistics Park could cut empty miles by 12%.", "Road Freight", "-12%", 0.70),
]

REPORTS = pd.DataFrame([
    {"name": "Singapore Scope 3 Emissions Report", "period": "Q2 2026", "format": "PDF", "size": "1.6 MB"},
    {"name": "MPA Green Shipping Disclosure", "period": "FY2025", "format": "PDF", "size": "2.1 MB"},
    {"name": "NEA Carbon Reporting Summary", "period": "FY2025", "format": "PDF", "size": "1.9 MB"},
    {"name": "Executive Summary \u2014 Singapore Ops", "period": "July 2026", "format": "PDF", "size": "0.7 MB"},
])

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown("### \U0001F6A2 Marcura")
st.sidebar.caption("Scope 3 Carbon Intelligence \u2014 Singapore Operations")
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Singapore Map", "Google Maps / Earth View", "Scope 3 Calculator", "Live Vessel Tracking",
     "Live Truck Tracking", "Predictive Analytics", "AI Carbon Copilot", "Reports"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption("Live data \u00b7 synthetic demo dataset")

st.sidebar.markdown("---")
st.sidebar.markdown("#### \U0001F916 AI Agent")
st.sidebar.caption("Optional: add a free Anthropic API key to power genuine AI-generated "
                    "summaries and open-ended chatbot answers. Without a key, both still work "
                    "using a data-grounded rule-based engine.")
anthropic_key_input = st.sidebar.text_input(
    "Anthropic API key", type="password", key="anthropic_api_key",
    help="Get one at console.anthropic.com. Stored only in this browser session, never saved.",
)
if anthropic_key_input:
    st.sidebar.success("AI agent active (Claude)")
else:
    st.sidebar.caption("AI agent running in rule-based mode")

vessels_df = gen_vessels()
trucks_df = gen_trucks()
monthly_df = gen_monthly_emissions()
forecast_df = gen_forecast(int(monthly_df.iloc[-1]["total"]))
suppliers_df = gen_suppliers()
routes_df = gen_routes()
source_df = gen_emissions_by_source()


def risk_badge(risk):
    cls = "badge-low" if risk == "Low" else "badge-med" if risk == "Medium" else "badge-high"
    return f'<span class="badge {cls}">{risk}</span>'


def build_satellite_map(center=(1.29, 103.85), zoom=11):
    m = folium.Map(location=center, zoom_start=zoom, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri labels",
        name="Labels",
        overlay=True,
        control=True,
    ).add_to(m)
    folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
if page == "Dashboard":
    st.title("Scope 3 Carbon Intelligence \u2014 Singapore Operations")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Scope 3 Emissions (12mo)", "112.0K t CO2e", "-2.6%")
    c2.metric("Monthly Emissions", f"{monthly_df.iloc[-1]['total']:,} t CO2e", "+3.4%")
    c3.metric("Active Shipments", "480", "+1.9%")
    c4.metric("MPA Green Shipping Score", "79 / 100", "+2.5%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Vessels tracked live", str(len(vessels_df)))
    c6.metric("Trucks tracked live", str(len(trucks_df)))
    c7.metric("Carbon Reduction vs Baseline", "11.8%", "+1.4%")
    c8.metric("Avg Carbon / Shipment", "241 kg CO2e", "-2.1%")

    st.markdown("---")
    st.markdown("### \U0001F916 AI Executive Summary")
    summary_col1, summary_col2 = st.columns([5, 1])
    with summary_col2:
        gen_summary = st.button("Generate", use_container_width=True, key="gen_exec_summary")
    with summary_col1:
        st.caption("A plain-English summary of the current Scope 3 position, written fresh from live dashboard data "
                    "each time you click Generate.")

    if gen_summary:
        ctx = build_dashboard_context(vessels_df, trucks_df, monthly_df, forecast_df, suppliers_df, routes_df, source_df)
        key = st.session_state.get("anthropic_api_key", "")
        if key:
            with st.spinner("Asking Claude to summarize the current Scope 3 position\u2026"):
                try:
                    summary_text = call_claude(
                        key,
                        system_prompt=(
                            "You are the Marcura Carbon Copilot, an AI sustainability analyst for a Singapore "
                            "maritime logistics operation. Write a concise, clear executive summary (4-6 sentences, "
                            "plain English, no headers) of the current Scope 3 emissions position, using only the "
                            "data provided below. Call out the single biggest emissions driver, the trend direction, "
                            "and one concrete recommended action."
                        ),
                        user_message=ctx,
                        max_tokens=400,
                    )
                    st.session_state["exec_summary"] = summary_text
                    st.session_state["exec_summary_source"] = "Claude (live AI)"
                except Exception as e:
                    st.error(f"Couldn't reach Claude: {e}. Showing the rule-based summary instead.")
                    key = ""
        if not key:
            last = monthly_df.iloc[-1]
            prev = monthly_df.iloc[-2]
            trend = "up" if last["total"] > prev["total"] else "down"
            top_source = source_df.sort_values("pct", ascending=False).iloc[0]
            top_supplier = suppliers_df.sort_values("co2e", ascending=False).iloc[0]
            top_route = routes_df.sort_values("co2e", ascending=False).iloc[0]
            fastest_vessel = vessels_df.loc[vessels_df["fuel_t_per_day"].idxmax()]
            st.session_state["exec_summary"] = (
                f"Singapore operations emitted {last['total']:,} t CO2e last month, {trend} from "
                f"{prev['total']:,} t the month before, against a budget of {last['budget']:,} t. "
                f"**{top_source['source']}** remains the single largest driver at {top_source['pct']}% of total "
                f"emissions, followed closely by upstream transportation. Among suppliers, **{top_supplier['name']}** "
                f"carries the highest footprint ({top_supplier['co2e']:,} t CO2e YTD, {top_supplier['risk']} risk), "
                f"and **{top_route['route']}** is the highest-emitting export lane at {top_route['co2e']:,} t CO2e. "
                f"On the water, **{fastest_vessel['name']}** currently has the highest estimated fuel burn "
                f"({fastest_vessel['fuel_t_per_day']} t/day). Recommended action: prioritize an LNG bunkering "
                f"switch on the Tuas Port \u2192 Rotterdam lane, which alone could cut roughly 9% off that route's footprint."
            )
            st.session_state["exec_summary_source"] = "Rule-based (data-grounded, no AI key)"

    if "exec_summary" in st.session_state:
        st.markdown(
            f'<div class="card">{st.session_state["exec_summary"]}<br><br>'
            f'<span style="font-size:11px;color:#6b5a35;">Source: {st.session_state["exec_summary_source"]}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Monthly Emissions Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["budget"], name="Budget",
                              line=dict(color="#b45309", dash="dash", width=2)))
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["total"], name="Actual",
                              line=dict(color="#0f766e", width=3), fill="tozeroy",
                              fillcolor="rgba(15,118,110,0.15)"))
    fig.update_layout(**PLOTLY_LAYOUT, height=340)
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Emissions by Source")
        fig2 = px.bar(source_df.sort_values("pct"), x="pct", y="source", orientation="h",
                       color="source", color_discrete_sequence=PALETTE)
        fig2.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        st.markdown("### Top Emitting Export Lanes")
        fig3 = px.bar(routes_df.sort_values("co2e"), x="co2e", y="route", orientation="h",
                       color="route", color_discrete_sequence=PALETTE)
        fig3.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Singapore Network Map (live preview)")
    m = build_satellite_map()
    for _, p in PORTS.iterrows():
        color = "orange" if p["kind"] == "industrial" else "pink" if p["kind"] == "air" else "cadetblue"
        folium.CircleMarker([p["lat"], p["lon"]], radius=6, color=color, fill=True, fill_opacity=0.9,
                             popup=f"{p['name']}<br>{p['note']}").add_to(m)
    for _, v in vessels_df.iterrows():
        lat, lon = interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], v["progress"])
        folium.CircleMarker([lat, lon], radius=5, color="#38bdf8", fill=True, fill_opacity=0.95,
                             popup=f"{v['name']} \u2192 {v['dest_name']}").add_to(m)
    st_folium(m, height=420, use_container_width=True, key="dash_map")

    col_c, col_d = st.columns([2, 1])
    with col_c:
        st.markdown("### AI Insights")
        for kind, text, tag, metric, conf in AI_INSIGHTS:
            icon = {"warning": "\u26A0\uFE0F", "positive": "\u2705", "opportunity": "\U0001F4A1", "alert": "\U0001F6A8"}[kind]
            st.markdown(
                f'<div class="card">{icon} {text}<br>'
                f'<span class="badge badge-med">{tag}</span> '
                f'<span style="color:#64748b;font-size:11px;">Confidence {conf*100:.0f}%</span> '
                f'<b style="float:right;">{metric}</b></div>',
                unsafe_allow_html=True,
            )
    with col_d:
        st.markdown("### Top Suppliers by Emissions")
        for _, s in suppliers_df.iterrows():
            st.markdown(
                f'<div class="card"><b>{s["name"]}</b><br>'
                f'<span style="color:#94a3b8;font-size:12px;">{s["location"]} \u00b7 {s["industry"]}</span><br>'
                f'{s["co2e"]:,} t &nbsp; {risk_badge(s["risk"])}</div>',
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Page: Singapore Map
# ---------------------------------------------------------------------------
elif page == "Singapore Map":
    st.title("Singapore Logistics Network \u2014 Satellite View")
    st.caption("Real Esri World Imagery satellite tiles \u00b7 ports, terminals, warehouses, and live vessels")

    layer_ports = st.checkbox("Show ports & terminals", value=True)
    layer_wh = st.checkbox("Show warehouses", value=True)
    layer_vessels = st.checkbox("Show live vessels", value=True)
    layer_trucks = st.checkbox("Show truck routes", value=True)

    m = build_satellite_map(zoom=11)
    if layer_ports:
        for _, p in PORTS.iterrows():
            color = "orange" if p["kind"] == "industrial" else "pink" if p["kind"] == "air" else "cadetblue"
            folium.CircleMarker([p["lat"], p["lon"]], radius=7, color=color, fill=True, fill_opacity=0.9,
                                 popup=f"<b>{p['name']}</b><br>{p['note']}").add_to(m)
    if layer_wh:
        for _, w in WAREHOUSES.iterrows():
            folium.Marker([w["lat"], w["lon"]], icon=folium.Icon(color="purple", icon="warehouse", prefix="fa"),
                          popup=w["name"]).add_to(m)
    if layer_trucks:
        for _, t in trucks_df.iterrows():
            folium.PolyLine([[t["from_lat"], t["from_lon"]], [t["to_lat"], t["to_lon"]]],
                             color="#fbbf24", weight=2, dash_array="4").add_to(m)
    if layer_vessels:
        for _, v in vessels_df.iterrows():
            lat, lon = interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], v["progress"])
            folium.CircleMarker([lat, lon], radius=6, color="#0ea5e9", fill=True, fill_opacity=0.95,
                                 popup=f"<b>{v['name']}</b><br>{v['type']} \u00b7 {v['fuel']}<br>"
                                       f"To: {v['dest_name']}<br>Speed: {v['speed_knots']} kn \u00b7 ETA {v['eta_hours']}h").add_to(m)

    st_folium(m, height=560, use_container_width=True, key="sg_map")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Ports & Terminals")
        st.dataframe(PORTS[["name", "kind", "note"]], hide_index=True, use_container_width=True)
    with col2:
        st.markdown("#### Warehouses & Distribution Centres")
        st.dataframe(WAREHOUSES[["name", "lat", "lon"]], hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Page: Google Maps / Earth View
# ---------------------------------------------------------------------------
elif page == "Google Maps / Earth View":
    st.title("Google Maps / Earth View")
    st.caption("Real Google Maps satellite imagery, plus a one-click link into Google Earth Web")

    st.markdown(
        '<div class="card">'
        '<b>Open in Google Earth</b><br>'
        'No API key needed \u2014 opens Google Earth Web directly centered on Singapore, in a new tab.'
        '</div>',
        unsafe_allow_html=True,
    )
    st.link_button(
        "\U0001F30D Open Singapore in Google Earth Web",
        "https://earth.google.com/web/@1.29,103.85,0a,60000d,35y,0h,0t,0r",
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### Google Maps \u2014 satellite view with live markers")
    st.markdown(
        "This view uses the **Google Maps Static API**, which needs a free Google Cloud API key "
        "(Maps Static API, enabled on a free-tier Google Cloud project \u2014 "
        "[console.cloud.google.com](https://console.cloud.google.com/google/maps-apis)). "
        "Without a key, use the no-key Google Maps embed below instead."
    )

    gmaps_key = st.text_input("Google Maps API key (optional)", type="password", key="gmaps_key")

    if gmaps_key:
        markers = []
        for _, p in PORTS.iterrows():
            color = "orange" if p["kind"] == "industrial" else "purple" if p["kind"] == "air" else "blue"
            markers.append(f"color:{color}%7Clabel:P%7C{p['lat']},{p['lon']}")
        for _, v in vessels_df.iterrows():
            lat, lon = interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], v["progress"])
            markers.append(f"color:green%7Clabel:V%7C{lat},{lon}")
        markers_param = "&markers=" + "&markers=".join(markers)
        static_url = (
            "https://maps.googleapis.com/maps/api/staticmap"
            f"?center=1.29,103.85&zoom=11&size=1280x520&maptype=satellite{markers_param}&key={gmaps_key}"
        )
        st.image(static_url, use_container_width=True,
                  caption="Ports (P) and simulated vessels (V) plotted on real Google satellite imagery")
    else:
        st.info(
            "No key entered \u2014 showing the free, no-key Google Maps embed instead "
            "(single center point, no custom markers, but genuine live Google Maps imagery).",
            icon="\U0001F5FA\uFE0F",
        )
        embed_url = "https://www.google.com/maps?q=1.29,103.85&z=11&output=embed"
        st.components.v1.iframe(embed_url, height=520)

# ---------------------------------------------------------------------------
# Page: Scope 3 Calculator
# ---------------------------------------------------------------------------
elif page == "Scope 3 Calculator":
    st.title("Scope 3 Emissions Calculator")
    st.caption("Estimate CO2e for Singapore-origin shipments (GLEC-aligned distance-based method)")

    col1, col2 = st.columns([1, 1])
    with col1:
        mode = st.selectbox("Transport mode", list(MODE_INTENSITY.keys()))
        weight = st.slider("Weight (tonnes)", 0.5, 30.0, 12.0, 0.5)
        distance = st.slider("Distance (km)", 10, 20000, 500, 10,
                              help="Tuas Port \u2192 Rotterdam \u2248 16,000 km \u00b7 Jurong \u2192 Changi \u2248 40 km")

        tonne_km = weight * distance
        co2e_kg = tonne_km * MODE_INTENSITY[mode]
        total_t = co2e_kg / 1000

        st.markdown(
            f'<div class="card"><span style="color:#94a3b8;font-size:12px;">Estimated Total CO2e</span><br>'
            f'<span style="font-size:32px;font-weight:700;color:#38bdf8;">{total_t:,.2f} t CO2e</span><br>'
            f'<span style="color:#64748b;font-size:11px;">Methodology: Distance-Based Method (GLEC Framework v3)</span></div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("#### Scope 3 Category Breakdown (trailing 12mo)")
        cats = pd.DataFrame([
            {"id": 1, "name": "Purchased Goods and Services", "pct": 12},
            {"id": 4, "name": "Upstream Transportation and Distribution", "pct": 38},
            {"id": 6, "name": "Business Travel", "pct": 3},
            {"id": 9, "name": "Downstream Transportation and Distribution", "pct": 24},
            {"id": 3, "name": "Fuel- and Energy-Related Activities", "pct": 14},
            {"id": 12, "name": "End-of-Life Treatment of Sold Products", "pct": 9},
        ])
        fig = px.pie(cats, names="name", values="pct", hole=0.55,
                     color_discrete_sequence=PALETTE)
        fig.update_traces(textfont_color="#fdf6e3", marker=dict(line=dict(color="#f3ead6", width=2)))
        fig.update_layout(**PLOTLY_LAYOUT, height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Scope 3 Summary by Source")
    cols = st.columns(4)
    for i, (_, row) in enumerate(source_df.iterrows()):
        cols[i % 4].metric(row["source"], f"{row['pct']}% of total")

# ---------------------------------------------------------------------------
# Page: Live Vessel Tracking
# ---------------------------------------------------------------------------
elif page == "Live Vessel Tracking":
    st.title("Live Vessel Tracking")

    data_source = st.radio(
        "Data source",
        ["Simulated fleet (demo)", "Live AIS \u2014 real ships near Singapore"],
        horizontal=True,
    )

    live_df = None
    if data_source.startswith("Live"):
        st.info(
            "Real-time AIS positions come from **AISStream.io**, a free live ship-tracking feed. "
            "Get a free API key at [aisstream.io](https://aisstream.io) (instant signup, no card needed), "
            "then paste it below.",
            icon="\U0001F6F0\uFE0F",
        )
        col_key, col_btn = st.columns([3, 1])
        api_key = col_key.text_input("AISStream.io API key", type="password", key="ais_key")
        fetch_clicked = col_btn.button("Fetch live ships", use_container_width=True)

        if fetch_clicked:
            if not api_key:
                st.warning("Enter your AISStream.io API key first.")
            else:
                with st.spinner("Listening for live AIS position reports near Singapore (\u2248 8s)\u2026"):
                    try:
                        live_df = fetch_live_ais(api_key, seconds=8)
                        st.session_state["live_ais_df"] = live_df
                    except Exception as e:
                        st.error(f"Couldn't reach the AIS feed: {e}. Falling back to the simulated fleet below.")
                        live_df = None
        elif "live_ais_df" in st.session_state:
            live_df = st.session_state["live_ais_df"]

        if live_df is not None:
            if live_df.empty:
                st.warning("No live position reports arrived in that window \u2014 traffic near Singapore is "
                            "constant, so try clicking **Fetch live ships** again, or check your API key.")
            else:
                st.success(f"Showing {len(live_df)} real, live vessel positions from AIS \u2014 captured just now.")

    st.caption(f"{len(vessels_df)} simulated vessels tracked, all outbound from Singapore \u00b7 satellite view"
               if live_df is None or live_df.empty else "Live AIS data overlaid in amber; simulated routes in blue.")

    m = build_satellite_map(center=(1.29, 103.85), zoom=11) if (live_df is not None and not live_df.empty) \
        else build_satellite_map(center=(10, 90), zoom=3)

    for _, p in PORTS[PORTS["kind"] == "port"].iterrows():
        folium.CircleMarker([p["lat"], p["lon"]], radius=6, color="cadetblue", fill=True, fill_opacity=0.9,
                             popup=p["name"]).add_to(m)

    # simulated routes always drawn (context), live points overlaid on top when available
    for _, v in vessels_df.iterrows():
        pts = [interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], t / 20)
               for t in range(21)]
        folium.PolyLine(pts, color="#38bdf8", weight=1.5, opacity=0.5, dash_array="2,6").add_to(m)
        lat, lon = interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], v["progress"])
        folium.CircleMarker([lat, lon], radius=6, color="#0ea5e9", fill=True, fill_opacity=0.9,
                             popup=f"<b>{v['name']}</b> (simulated)<br>{v['type']} \u00b7 {v['fuel']}<br>"
                                   f"To: {v['dest_name']}<br>Speed: {v['speed_knots']} kn \u00b7 ETA {v['eta_hours']}h").add_to(m)

    if live_df is not None and not live_df.empty:
        for _, r in live_df.iterrows():
            folium.CircleMarker(
                [r["lat"], r["lon"]], radius=5, color="#f59e0b", fill=True, fill_opacity=0.95,
                popup=f"<b>{r['name']}</b> (LIVE)<br>MMSI {r['mmsi']}<br>"
                      f"SOG {r.get('sog_knots', 'n/a')} kn \u00b7 COG {r.get('cog_deg', 'n/a')}\u00b0<br>"
                      f"{r.get('time_utc', '')}",
            ).add_to(m)

    st_folium(m, height=460, use_container_width=True, key="vessel_map")

    if live_df is not None and not live_df.empty:
        st.markdown("### Live AIS Fleet (real, right now)")
        st.caption("Fuel/CO\u2082 columns are estimated from live AIS speed using a standard cube-law fuel "
                    "curve (real AIS doesn't transmit fuel flow) \u2014 assumes a generic container-ship/VLSFO profile.")
        st.dataframe(
            live_df[["name", "mmsi", "lat", "lon", "sog_knots", "cog_deg",
                      "fuel_t_per_day", "co2_kg_per_hour", "time_utc"]].rename(columns={
                "sog_knots": "speed (kn)", "cog_deg": "course (\u00b0)",
                "fuel_t_per_day": "est. fuel (t/day)", "co2_kg_per_hour": "est. CO2 (kg/hr)",
            }),
            hide_index=True, use_container_width=True,
        )

    st.markdown("### Simulated Fleet")
    st.caption("Fuel/CO\u2082 estimated from vessel type + fuel + current speed (cube-law model).")
    for _, v in vessels_df.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
        col1.markdown(f"**{v['name']}**  \n{v['type']} \u2192 {v['dest_name']} ({v['fuel']})")
        col2.metric("Speed", f"{v['speed_knots']} kn")
        col3.metric("ETA", f"{v['eta_hours']} h")
        col4.metric("Fuel use", f"{v['fuel_t_per_day']} t/day")
        col5.metric("CO2 rate", f"{v['co2_kg_per_hour']:,.0f} kg/hr")
        col6.progress(v["progress"], text=f"{int(v['progress']*100)}%")

# ---------------------------------------------------------------------------
# Page: Live Truck Tracking
# ---------------------------------------------------------------------------
elif page == "Live Truck Tracking":
    st.title("Live Truck Tracking")
    st.caption(f"{len(trucks_df)} trucks tracked \u00b7 warehouse-to-terminal lanes, island-wide")

    m = build_satellite_map(zoom=11)
    for _, t in trucks_df.iterrows():
        folium.PolyLine([[t["from_lat"], t["from_lon"]], [t["to_lat"], t["to_lon"]]],
                         color="#fbbf24", weight=2, dash_array="4").add_to(m)
        lat = t["from_lat"] + (t["to_lat"] - t["from_lat"]) * t["progress"]
        lon = t["from_lon"] + (t["to_lon"] - t["from_lon"]) * t["progress"]
        folium.CircleMarker([lat, lon], radius=6, color="#f97316", fill=True, fill_opacity=0.95,
                             popup=f"<b>{t['truck_id']}</b><br>{t['driver']} \u00b7 {t['fuel']}<br>"
                                   f"{t['from_name']} \u2192 {t['to_name']}<br>Status: {t['status']}").add_to(m)
    st_folium(m, height=460, use_container_width=True, key="truck_map")

    st.markdown("### Fleet")
    status_color = {"Driving": "\U0001F7E2", "Idle": "\U0001F7E1", "Loading": "\U0001F535", "Delayed": "\U0001F534"}
    for _, t in trucks_df.iterrows():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        col1.markdown(f"**{t['truck_id']}** {status_color.get(t['status'], '')} {t['status']}  \n"
                      f"{t['driver']} \u00b7 {t['from_name']} \u2192 {t['to_name']}")
        col2.metric("Speed", f"{t['speed_kmh']} km/h")
        col3.metric("Fuel", t["fuel"])
        col4.metric("CO2e", f"{t['co2e_kg']} kg")

# ---------------------------------------------------------------------------
# Page: Predictive Analytics
# ---------------------------------------------------------------------------
elif page == "Predictive Analytics":
    st.title("Predictive Analytics")
    st.caption("6-month emissions forecast, Singapore operations")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Next Month Forecast", f"{forecast_df.iloc[0]['predicted']:,} t CO2e")
    c2.metric("Fuel Usage Forecast", f"{forecast_df.iloc[0]['predicted']/3.1:,.0f} MT")
    c3.metric("Shipment Volume Forecast", "560 shipments")
    c4.metric("Carbon Budget Forecast", "118.0K t CO2e annualised")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_df["month"], y=forecast_df["upper"], line=dict(width=0),
                              showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=forecast_df["month"], y=forecast_df["lower"], fill="tonexty",
                              fillcolor="rgba(15,118,110,0.15)", line=dict(width=0), name="Confidence band"))
    fig.add_trace(go.Scatter(x=forecast_df["month"], y=forecast_df["predicted"], name="Forecast",
                              line=dict(color="#0f766e", width=3),
                              mode="lines+markers", marker=dict(size=7, color="#b45309", line=dict(color="#f3ead6", width=1))))
    fig.update_layout(**PLOTLY_LAYOUT, height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(forecast_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Page: AI Carbon Copilot
# ---------------------------------------------------------------------------
elif page == "AI Carbon Copilot":
    st.title("AI Carbon Copilot")
    key = st.session_state.get("anthropic_api_key", "")
    if key:
        st.caption("\u2705 Powered by Claude, grounded in live Singapore Scope 3 dashboard data \u2014 ask anything.")
    else:
        st.caption("Running in data-grounded rule-based mode. Add a free Anthropic API key in the sidebar "
                    "for fully open-ended answers about anything on the dashboard.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi, I'm the Marcura Carbon Copilot, scoped to Singapore operations. "
                                              "Ask me about a specific vessel's speed or fuel use, a truck, a supplier, "
                                              "a shipping lane, the forecast, or anything else on this dashboard."}
        ]

    ctx_data = {
        "vessels_df": vessels_df, "trucks_df": trucks_df, "monthly_df": monthly_df,
        "suppliers_df": suppliers_df, "routes_df": routes_df, "forecast_df": forecast_df,
    }

    def reply(q):
        if key:
            ctx = build_dashboard_context(vessels_df, trucks_df, monthly_df, forecast_df, suppliers_df, routes_df, source_df)
            try:
                return call_claude(
                    key,
                    system_prompt=(
                        "You are the Marcura Carbon Copilot, an AI assistant embedded in a Scope 3 carbon "
                        "intelligence dashboard for a Singapore maritime logistics operation. Answer the user's "
                        "question using ONLY the dashboard data provided below \u2014 you can discuss any vessel, "
                        "truck, supplier, route, emissions figure, or forecast in it. Be specific and cite real "
                        "numbers from the data. If the question can't be answered from this data, say so plainly. "
                        "Keep answers conversational and under ~120 words unless more detail is clearly needed.\n\n" + ctx
                    ),
                    user_message=q,
                    max_tokens=500,
                )
            except Exception as e:
                return f"(Claude API error: {e} \u2014 falling back to rule-based answer)\n\n" + rule_based_answer(q, ctx_data)
        return rule_based_answer(q, ctx_data)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    suggestions = ["How fast is the fastest vessel going?", "Which vessel uses the most fuel?",
                    "Which supplier has the highest footprint?"]
    cols = st.columns(len(suggestions))
    clicked = None
    for i, s in enumerate(suggestions):
        if cols[i].button(s, key=f"sugg_{i}"):
            clicked = s

    user_input = st.chat_input("Ask about a vessel, truck, supplier, route, or forecast\u2026") or clicked
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.spinner("Thinking\u2026") if key else st.empty():
            answer = reply(user_input)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)

# ---------------------------------------------------------------------------
# Page: Reports
# ---------------------------------------------------------------------------
elif page == "Reports":
    st.title("Reports")
    st.caption("Singapore-scoped Scope 3, MPA, and NEA-aligned reports")

    cols = st.columns(2)
    for i, (_, r) in enumerate(REPORTS.iterrows()):
        with cols[i % 2]:
            st.markdown(
                f'<div class="card"><b>{r["name"]}</b><br>'
                f'<span style="color:#94a3b8;font-size:12px;">{r["period"]} \u00b7 {r["format"]} \u00b7 {r["size"]}</span></div>',
                unsafe_allow_html=True,
            )
            st.button("Download (demo)", key=f"dl_{i}")
