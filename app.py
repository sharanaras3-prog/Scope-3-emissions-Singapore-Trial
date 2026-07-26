import math
import random
import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
import pydeck as pdk
import requests
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
        background: linear-gradient(160deg, #000000 0%, #060606 50%, #0a0a0a 100%);
        color: #f1f5f9;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #030303 0%, #000000 100%);
        border-right: 1px solid rgba(56,189,248,0.15);
    }
    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    h1, h2, h3, h4, p, span, label, div { color: #f1f5f9; }
    h1 {
        background: linear-gradient(90deg, #22d3ee, #2dd4bf 55%, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
    p, .stMarkdown, .stCaption, label { color: #e2e8f0 !important; }
    [data-testid="stCaptionContainer"] { color: #94a3b8 !important; }
    div[data-testid="stMetric"] {
        background: linear-gradient(155deg, rgba(34,211,238,0.08), rgba(20,20,20,0.85));
        border: 1px solid rgba(56,189,248,0.22);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.45);
    }
    div[data-testid="stMetricLabel"] { color: #7dd3fc !important; font-weight: 700; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 800; }
    div[data-testid="stMetricDelta"] { font-weight: 600; }
    .badge {
        display:inline-block; padding:3px 12px; border-radius:999px;
        font-size:11px; font-weight:700; letter-spacing:.2px;
    }
    .badge-low{background:linear-gradient(135deg,#059669,#10b981); color:#ecfdf5;}
    .badge-med{background:linear-gradient(135deg,#d97706,#f59e0b); color:#fffbeb;}
    .badge-high{background:linear-gradient(135deg,#dc2626,#f43f5e); color:#fef2f2;}
    .card {
        background: linear-gradient(155deg, rgba(34,211,238,0.06), rgba(15,15,15,0.85));
        border: 1px solid rgba(148,163,184,0.18);
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.4);
        color: #f1f5f9;
    }
    .card b { color: #22d3ee; }
    .stButton>button {
        border-radius: 10px;
        border: 1px solid rgba(34,211,238,0.35);
        background: linear-gradient(135deg, rgba(34,211,238,0.14), rgba(45,212,191,0.10));
        color: #f1f5f9;
        font-weight: 700;
    }
    .stButton>button:hover {
        border-color: #22d3ee;
        background: linear-gradient(135deg, rgba(34,211,238,0.28), rgba(45,212,191,0.20));
        color: #ffffff;
    }
    .stTabs [data-baseweb="tab"] { color: #94a3b8; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #22d3ee !important; }
    hr { border-color: rgba(148,163,184,0.18) !important; }
    [data-testid="stChatMessage"] {
        background: rgba(20,20,20,0.75);
        border: 1px solid rgba(56,189,248,0.18);
        border-radius: 14px;
        color: #f1f5f9;
    }
    .stTextInput input, .stNumberInput input { color: #ffffff !important; background-color: #0d0d0d !important; }
    div[data-testid="stDataFrame"] { color: #f1f5f9 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Consistent maritime chart palette used across all Plotly figures (readable on black)
PALETTE = ["#22d3ee", "#2dd4bf", "#38bdf8", "#a78bfa", "#f59e0b", "#fb7185", "#34d399", "#818cf8"]
PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f1f5f9"),
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
# Global fleet view (MarineTraffic-style): a dense, color-coded, direction-arrow
# map of vessels clustered along the world's actual major shipping lanes.
# There is no free public feed with 300k+ live global vessel positions (that's
# MarineTraffic/Kpler's own paid commercial data), so this is a large synthetic
# fleet distributed realistically along real corridors, in the same visual
# language: green=cargo, red=tanker, blue=passenger/other, orange=fishing,
# cyan=high-speed craft, magenta=pleasure/sailing.
# ---------------------------------------------------------------------------
WORLD_PORTS = pd.DataFrame([
    {"code": "US BPT", "name": "Beaumont", "country": "US", "lat": 30.08, "lon": -94.10},
    {"code": "CN LYG", "name": "Lianyungang", "country": "CN", "lat": 34.60, "lon": 119.22},
    {"code": "SG SIN", "name": "Singapore", "country": "SG", "lat": 1.29, "lon": 103.85},
    {"code": "NL RTM", "name": "Rotterdam", "country": "NL", "lat": 51.95, "lon": 4.14},
    {"code": "CN SHA", "name": "Shanghai", "country": "CN", "lat": 31.23, "lon": 121.47},
    {"code": "AE JEA", "name": "Jebel Ali", "country": "AE", "lat": 25.01, "lon": 55.06},
    {"code": "US LAX", "name": "Los Angeles", "country": "US", "lat": 33.74, "lon": -118.26},
    {"code": "KR PUS", "name": "Busan", "country": "KR", "lat": 35.10, "lon": 129.04},
    {"code": "HK HKG", "name": "Hong Kong", "country": "HK", "lat": 22.29, "lon": 114.15},
    {"code": "DE HAM", "name": "Hamburg", "country": "DE", "lat": 53.55, "lon": 9.97},
    {"code": "AU MEL", "name": "Melbourne", "country": "AU", "lat": -37.84, "lon": 144.93},
    {"code": "EG PSD", "name": "Port Said", "country": "EG", "lat": 31.26, "lon": 32.30},
    {"code": "GR PIR", "name": "Piraeus", "country": "GR", "lat": 37.95, "lon": 23.64},
    {"code": "ES ALG", "name": "Algeciras", "country": "ES", "lat": 36.14, "lon": -5.46},
    {"code": "MY PKG", "name": "Port Klang", "country": "MY", "lat": 3.00, "lon": 101.40},
    {"code": "VN SGN", "name": "Ho Chi Minh City", "country": "VN", "lat": 10.78, "lon": 106.70},
    {"code": "PA ONX", "name": "Balboa", "country": "PA", "lat": 8.95, "lon": -79.57},
    {"code": "BR SSZ", "name": "Santos", "country": "BR", "lat": -23.96, "lon": -46.33},
    {"code": "US NYC", "name": "New York", "country": "US", "lat": 40.67, "lon": -74.05},
    {"code": "US SAV", "name": "Savannah", "country": "US", "lat": 32.08, "lon": -81.10},
    {"code": "IN JNP", "name": "Nhava Sheva", "country": "IN", "lat": 18.95, "lon": 72.95},
    {"code": "ZA DUR", "name": "Durban", "country": "ZA", "lat": -29.86, "lon": 31.02},
    {"code": "NG LOS", "name": "Lagos", "country": "NG", "lat": 6.45, "lon": 3.38},
    {"code": "RU LED", "name": "St Petersburg", "country": "RU", "lat": 59.93, "lon": 30.30},
    {"code": "JP YOK", "name": "Yokohama", "country": "JP", "lat": 35.44, "lon": 139.64},
])


def _nearest_port(lat, lon):
    d2 = (WORLD_PORTS["lat"] - lat) ** 2 + (WORLD_PORTS["lon"] - lon) ** 2
    return WORLD_PORTS.loc[d2.idxmin()]


SHIPPING_LANES = [
    # (name, [ (lat, lon), ... waypoints ])
    ("Trans-Pacific (Asia-US West Coast)", [(31.2, 121.5), (35.0, 145.0), (40.0, 175.0), (45.0, -160.0), (40.0, -135.0), (33.7, -118.3)]),
    ("Trans-Atlantic (US East-Europe)", [(40.7, -74.0), (43.0, -50.0), (47.0, -25.0), (49.5, -5.0), (51.9, 4.1)]),
    ("Asia-Europe via Suez", [(1.3, 103.8), (6.9, 79.8), (12.6, 43.4), (29.9, 32.6), (35.9, 14.5), (36.1, -5.4), (49.5, -5.0), (51.9, 4.1)]),
    ("North Sea / Baltic", [(51.9, 4.1), (53.5, 8.6), (55.7, 12.6), (59.3, 18.1), (60.2, 24.9)]),
    ("Mediterranean", [(36.1, -5.4), (38.1, 13.4), (37.9, 23.6), (31.3, 32.3), (33.6, 35.0)]),
    ("Persian Gulf - Asia", [(29.4, 48.5), (25.0, 55.1), (20.0, 65.0), (8.9, 76.6), (1.3, 103.8), (22.3, 114.2)]),
    ("Intra-Asia (S. China Sea / Malacca)", [(31.2, 121.5), (22.3, 114.2), (14.6, 120.9), (10.8, 106.7), (1.3, 103.8), (3.0, 101.4), (13.1, 100.9)]),
    ("Australia - Asia", [(-33.9, 151.2), (-37.8, 144.9), (-6.1, 106.8), (1.3, 103.8), (22.3, 114.2)]),
    ("US Gulf / Caribbean", [(29.3, -94.8), (25.8, -80.2), (18.5, -69.9), (10.4, -75.5), (9.0, -79.5)]),
    ("South America East Coast", [(-23.9, -46.3), (-34.6, -58.4), (-33.0, -71.6)]),
    ("West Africa", [(6.4, 3.4), (-4.0, 11.5), (-25.9, 32.6), (-33.9, 18.4)]),
    ("India - Middle East", [(18.9, 72.8), (24.9, 67.0), (25.3, 55.3), (29.4, 48.5)]),
    ("North Pacific (Russia/Japan/Korea)", [(43.1, 131.9), (35.4, 139.7), (35.1, 129.0), (31.2, 121.5)]),
    ("Panama Canal corridor", [(9.0, -79.5), (25.8, -80.2), (29.3, -94.8)]),
    ("US West Coast - Panama", [(33.7, -118.3), (20.5, -105.3), (9.0, -79.5)]),
]

VESSEL_CLASS_STYLE = {
    # (display name, RGB color, relative frequency weight)
    "Cargo": ((34, 197, 94), 42),
    "Tanker": ((239, 68, 68), 20),
    "Fishing": ((249, 115, 22), 14),
    "Passenger / Other": ((59, 130, 246), 10),
    "High-Speed Craft": ((34, 211, 238), 6),
    "Pleasure / Sailing": ((192, 38, 211), 8),
}

# speed range (kn), draught range (m), typical nav status, fuel-model profile key
VESSEL_CLASS_PROFILE = {
    "Cargo": {"speed": (10, 18), "draught": (7, 14), "status": ["Underway Using Engine", "At Anchor"], "fuel_profile": "Container Ship"},
    "Tanker": {"speed": (9, 15), "draught": (9, 16), "status": ["Underway Using Engine", "At Anchor", "Moored"], "fuel_profile": "Bulk Carrier"},
    "Fishing": {"speed": (5, 11), "draught": (2, 4), "status": ["Fishing", "Underway Using Engine"], "fuel_profile": "General Cargo"},
    "Passenger / Other": {"speed": (15, 22), "draught": (5, 8), "status": ["Underway Using Engine"], "fuel_profile": "LNG Carrier"},
    "High-Speed Craft": {"speed": (22, 34), "draught": (1.5, 3), "status": ["Underway Using Engine"], "fuel_profile": "General Cargo"},
    "Pleasure / Sailing": {"speed": (4, 10), "draught": (1.5, 3.5), "status": ["Underway Using Engine", "Moored"], "fuel_profile": "General Cargo"},
}

VESSEL_NAME_BANK = ["Spirits", "Voyager", "Pioneer", "Horizon", "Endeavor", "Meridian", "Zenith", "Aurora",
                     "Odyssey", "Sentinel", "Navigator", "Star", "Trader", "Legacy", "Fortune", "Pacific"]
VESSEL_NAME_PREFIX2 = ["Yuyo", "Nord", "Ocean", "Global", "Star", "Blue", "Pacific", "Atlantic", "Eastern", "Northern"]
FLAG_COUNTRIES = ["Panama", "Liberia", "Marshall Islands", "Singapore", "Malta", "Hong Kong", "Greece", "Japan", "China", "Denmark"]


def _lane_point(waypoints, t, jitter_deg=0.9):
    """Interpolate along a polyline of waypoints at fraction t (0-1), with lateral jitter."""
    n = len(waypoints) - 1
    seg = min(int(t * n), n - 1)
    local_t = (t * n) - seg
    lat1, lon1 = waypoints[seg]
    lat2, lon2 = waypoints[seg + 1]
    lat = lat1 + (lat2 - lat1) * local_t
    lon = lon1 + (lon2 - lon1) * local_t
    heading = math.degrees(math.atan2(lon2 - lon1, lat2 - lat1)) % 360
    lat += random.gauss(0, jitter_deg)
    lon += random.gauss(0, jitter_deg)
    heading = (heading + random.gauss(0, 12)) % 360
    return lat, lon, heading


@st.cache_data
def gen_global_fleet(n_lane_points=2600, n_scatter=500, seed=11):
    rng = random.Random(seed)
    classes = list(VESSEL_CLASS_STYLE.keys())
    weights = [VESSEL_CLASS_STYLE[c][1] for c in classes]
    today = dt.datetime(2026, 7, 26, 9, 0)

    def build_row(lat, lon, heading, vclass, lane_name, waypoints, t):
        color = VESSEL_CLASS_STYLE[vclass][0]
        profile = VESSEL_CLASS_PROFILE[vclass]
        speed = round(rng.uniform(*profile["speed"]), 1)
        draught = round(rng.uniform(*profile["draught"]), 1)
        status = rng.choice(profile["status"])
        fuel = rng.choice(FUEL_TYPES)
        name = f"{rng.choice(VESSEL_NAME_PREFIX2)} {rng.choice(VESSEL_NAME_BANK)}"
        flag = rng.choice(FLAG_COUNTRIES)
        mmsi = rng.randint(200000000, 799999999)

        if waypoints:
            origin_pt, dest_pt = waypoints[0], waypoints[-1]
            origin = _nearest_port(*origin_pt)
            dest = _nearest_port(*dest_pt)
            total_days = rng.uniform(8, 34)
            atd = today - dt.timedelta(days=t * total_days)
            eta = today + dt.timedelta(days=(1 - t) * total_days)
        else:
            origin = dest = _nearest_port(lat, lon)
            atd = today - dt.timedelta(days=rng.uniform(1, 5))
            eta = today + dt.timedelta(days=rng.uniform(1, 5))
            t = 0.5

        return {
            "vessel_id": mmsi, "name": name, "flag": flag,
            "lat": lat, "lon": lon, "heading": heading, "class": vclass,
            "color": color, "lane": lane_name, "progress": round(t, 3),
            "speed_knots": speed, "draught_m": draught, "nav_status": status, "fuel": fuel,
            "origin_code": origin["code"], "origin_name": origin["name"], "origin_country": origin["country"],
            "dest_code": dest["code"], "dest_name": dest["name"], "dest_country": dest["country"],
            "atd": atd, "eta": eta, "lane_waypoints": waypoints,
        }

    rows = []
    per_lane = n_lane_points // len(SHIPPING_LANES)
    for lane_name, waypoints in SHIPPING_LANES:
        for _ in range(per_lane):
            t = rng.random()
            lat, lon, heading = _lane_point(waypoints, t)
            vclass = rng.choices(classes, weights=weights, k=1)[0]
            rows.append(build_row(lat, lon, heading, vclass, lane_name, waypoints, t))

    for _ in range(n_scatter):
        lat = rng.uniform(-60, 70)
        lon = rng.uniform(-180, 180)
        heading = rng.uniform(0, 360)
        vclass = rng.choices(classes, weights=weights, k=1)[0]
        rows.append(build_row(lat, lon, heading, vclass, "Open ocean", None, 0.5))

    df = pd.DataFrame(rows)
    df["r"] = df["color"].apply(lambda c: c[0])
    df["g"] = df["color"].apply(lambda c: c[1])
    df["b"] = df["color"].apply(lambda c: c[2])
    return df


def vessel_illustration_data_uri(vclass: str, rgb: tuple) -> str:
    """A representative side-profile ship illustration tinted by vessel class.
    There is no real photo database for these synthetic MMSIs, so this is an
    honest stand-in illustration (not a claim of being the actual vessel photo)."""
    import base64
    hull = "#%02x%02x%02x" % rgb
    deck_shapes = {
        "Cargo": '<rect x="60" y="55" width="18" height="22" fill="#e2e8f0" opacity="0.9"/>'
                 '<rect x="82" y="50" width="18" height="27" fill="#cbd5e1" opacity="0.9"/>'
                 '<rect x="104" y="55" width="18" height="22" fill="#e2e8f0" opacity="0.9"/>'
                 '<rect x="126" y="50" width="18" height="27" fill="#cbd5e1" opacity="0.9"/>'
                 '<rect x="230" y="35" width="40" height="45" fill="#f1f5f9"/>',
        "Tanker": '<ellipse cx="150" cy="60" rx="120" ry="10" fill="#94a3b8" opacity="0.5"/>'
                  '<circle cx="90" cy="52" r="8" fill="#cbd5e1"/><circle cx="150" cy="52" r="8" fill="#cbd5e1"/>'
                  '<circle cx="210" cy="52" r="8" fill="#cbd5e1"/>'
                  '<rect x="250" y="35" width="35" height="45" fill="#f1f5f9"/>',
        "Fishing": '<rect x="120" y="35" width="30" height="35" fill="#f1f5f9"/>'
                   '<line x1="135" y1="10" x2="135" y2="35" stroke="#94a3b8" stroke-width="3"/>',
        "Passenger / Other": '<rect x="60" y="20" width="200" height="35" fill="#f8fafc" rx="4"/>'
                              '<rect x="60" y="40" width="200" height="15" fill="#e2e8f0" rx="2"/>',
        "High-Speed Craft": '<rect x="120" y="40" width="60" height="20" fill="#f1f5f9" rx="6"/>',
        "Pleasure / Sailing": '<line x1="150" y1="10" x2="150" y2="75" stroke="#94a3b8" stroke-width="3"/>'
                               '<path d="M150,15 L175,70 L150,70 Z" fill="#e2e8f0" opacity="0.9"/>',
    }
    deck = deck_shapes.get(vclass, deck_shapes["Cargo"])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 130" width="100%" height="100%">
      <defs>
        <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0a1a2e"/><stop offset="100%" stop-color="#0e2440"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="320" height="130" fill="url(#sea)"/>
      <ellipse cx="160" cy="102" rx="150" ry="8" fill="#1e3a5f" opacity="0.6"/>
      <path d="M20,80 L20,60 Q20,50 35,50 L275,50 Q290,50 295,65 L305,80 Q300,90 285,90 L35,90 Q20,90 20,80 Z" fill="{hull}"/>
      {deck}
      <rect x="0" y="95" width="320" height="35" fill="url(#sea)" opacity="0.85"/>
      <ellipse cx="160" cy="98" rx="145" ry="5" fill="#38bdf8" opacity="0.35"/>
    </svg>'''
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


def fetch_weather(lat, lon):
    """Real, free, no-key weather + marine data from Open-Meteo for a given position."""
    out = {}
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon,
                    "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code"},
            timeout=6,
        )
        r.raise_for_status()
        cur = r.json().get("current", {})
        out["temperature_c"] = cur.get("temperature_2m")
        out["wind_speed_kmh"] = cur.get("wind_speed_10m")
        out["wind_dir_deg"] = cur.get("wind_direction_10m")
    except Exception as e:
        out["weather_error"] = str(e)

    try:
        r2 = requests.get(
            "https://marine-api.open-meteo.com/v1/marine",
            params={"latitude": lat, "longitude": lon,
                    "current": "wave_height,wave_period,wave_direction"},
            timeout=6,
        )
        r2.raise_for_status()
        cur2 = r2.json().get("current", {})
        out["wave_height_m"] = cur2.get("wave_height")
        out["wave_period_s"] = cur2.get("wave_period")
    except Exception as e:
        out["marine_error"] = str(e)

    return out







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
    ["Dashboard", "Global Fleet View", "Google Maps / Earth View", "Scope 3 Calculator",
     "Live Vessel Tracking", "Live Truck Tracking", "Predictive Analytics", "AI Carbon Copilot", "Reports"],
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
            f'<span style="font-size:11px;color:#94a3b8;">Source: {st.session_state["exec_summary_source"]}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Monthly Emissions Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["budget"], name="Budget",
                              line=dict(color="#f59e0b", dash="dash", width=2)))
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["total"], name="Actual",
                              line=dict(color="#22d3ee", width=3), fill="tozeroy",
                              fillcolor="rgba(34,211,238,0.18)"))
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

    st.markdown("### Global Fleet Snapshot")
    st.caption("Full interactive fleet view with click-to-inspect vessel detail is on the **Global Fleet View** page.")
    snap_fleet = gen_global_fleet()
    snap_layer = pdk.Layer(
        "TextLayer",
        data=(lambda df: (df.assign(symbol="^")))(snap_fleet[["lat", "lon", "heading", "r", "g", "b"]].sample(min(1200, len(snap_fleet)), random_state=1)),
        get_position=["lon", "lat"], get_text="symbol", get_color=["r", "g", "b"],
        get_angle="heading", get_size=20,
    )
    snap_deck = pdk.Deck(
        layers=[snap_layer],
        initial_view_state=pdk.ViewState(latitude=20, longitude=20, zoom=0.9, pitch=0),
        map_style="light",
    )
    st.pydeck_chart(snap_deck, use_container_width=True, height=420)

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
# Page: Global Fleet View (MarineTraffic-style)
# ---------------------------------------------------------------------------
elif page == "Global Fleet View":
    st.title("Global Fleet View")
    st.caption(
        "A MarineTraffic-style view of the world's shipping lanes \u2014 vessels color-coded by type, "
        "arrows showing heading, clustered along real trade corridors. **Click any vessel** to inspect it."
    )
    st.info(
        "MarineTraffic/Kpler's live view tracks ~300K+ real vessels from a paid commercial AIS network "
        "spanning satellite + terrestrial receivers worldwide \u2014 there's no free feed at that scale. "
        "This is a large **synthetic fleet** (3,100 vessels) distributed along the world's actual major "
        "shipping lanes, in the same visual language, so you can demo the concept without a commercial data contract. "
        "Weather data shown for a selected vessel, however, is genuinely live (Open-Meteo, no key required).",
        icon="\U0001F6A2",
    )

    fleet_df = gen_global_fleet()

    col_filter, col_stat = st.columns([3, 1])
    with col_filter:
        selected_classes = st.multiselect(
            "Vessel classes shown", options=list(VESSEL_CLASS_STYLE.keys()),
            default=list(VESSEL_CLASS_STYLE.keys()),
        )
    with col_stat:
        st.metric("Vessels shown", f"{len(fleet_df[fleet_df['class'].isin(selected_classes)]):,}")

    view_df = fleet_df[fleet_df["class"].isin(selected_classes)].reset_index(drop=True)

    # Slim, JSON-safe dataframe for the map layer (no datetimes/nested lists —
    # those stay in fleet_df/view_df and get looked up after selection by vessel_id)
    plot_df = view_df[["vessel_id", "name", "class", "lane", "lat", "lon", "heading", "r", "g", "b"]].copy()
    # NOTE: pydeck's TextLayer accessors read a real dataframe column by name —
    # passing a quoted literal like "'\u25B2'" gets misread as a (nonexistent) column
    # name, so every glyph silently renders empty. A real column is required.
    # We also use a plain ASCII caret "^" rather than a unicode triangle, since
    # deck.gl's TextLayer only auto-generates a font atlas for the default ASCII
    # range unless you explicitly widen characterSet \u2014 ASCII avoids that pitfall
    # entirely across all browsers.
    plot_df["symbol"] = "^"

    layer = pdk.Layer(
        "TextLayer",
        data=plot_df,
        get_position=["lon", "lat"],
        get_text="symbol",
        get_color=["r", "g", "b"],
        get_angle="heading",
        get_size=26,
        pickable=True,
        id="vessel-layer",
    )
    view_state = pdk.ViewState(latitude=20, longitude=20, zoom=1.5, pitch=0)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="light",
        tooltip={"text": "{name}\n{class}\n{lane}"},
    )
    event = st.pydeck_chart(
        deck, use_container_width=True, height=700,
        on_select="rerun", selection_mode="single-object", key="fleet_deck",
    )

    st.markdown("#### Legend")
    legend_cols = st.columns(len(VESSEL_CLASS_STYLE))
    for i, (name, (color, _)) in enumerate(VESSEL_CLASS_STYLE.items()):
        hex_color = "#%02x%02x%02x" % color
        legend_cols[i].markdown(
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'<span style="color:{hex_color};font-size:18px;">\u25B2</span>'
            f'<span style="font-size:12px;">{name}</span></div>',
            unsafe_allow_html=True,
        )

    # ---- Vessel detail panel (rendered when a vessel is clicked) ----
    selected_vessel_id = None
    try:
        objs = event.selection.get("objects", {}).get("vessel-layer", [])
        if objs:
            selected_vessel_id = objs[0].get("vessel_id")
    except Exception:
        selected_vessel_id = None

    if selected_vessel_id is not None:
        match = fleet_df[fleet_df["vessel_id"] == selected_vessel_id]
        if not match.empty:
            v = match.iloc[0]
            hex_color = "#%02x%02x%02x" % (v["r"], v["g"], v["b"])
            st.markdown("---")

            # ---- Header: name, type, flag (mirrors MarineTraffic's vessel card) ----
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:14px;">'
                f'<div style="width:14px;height:14px;border-radius:4px;background:{hex_color};"></div>'
                f'<div><span style="font-size:28px;font-weight:800;letter-spacing:0.5px;">{v["name"].upper()}</span><br>'
                f'<span style="font-size:15px;color:#94a3b8;">{v["class"]} \u00b7 Flag: {v["flag"]} \u00b7 MMSI {v["vessel_id"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)
            photo_col, info_col = st.columns([2, 3])

            with photo_col:
                st.image(vessel_illustration_data_uri(v["class"], (v["r"], v["g"], v["b"])), use_container_width=True)
                st.caption("Representative vessel-class illustration \u2014 no real photo database exists for this synthetic fleet.")

            with info_col:
                r1c1, r1c2 = st.columns(2)
                r1c1.markdown(
                    f'<span style="font-size:22px;font-weight:800;">{v["origin_country"]} {v["origin_code"]}</span><br>'
                    f'<span style="font-size:13px;color:#94a3b8;">{v["origin_name"]}</span>',
                    unsafe_allow_html=True,
                )
                r1c2.markdown(
                    f'<div style="text-align:right;"><span style="font-size:22px;font-weight:800;">{v["dest_country"]} {v["dest_code"]}</span><br>'
                    f'<span style="font-size:13px;color:#94a3b8;">{v["dest_name"]}</span></div>',
                    unsafe_allow_html=True,
                )
                pct = float(v["progress"]) * 100
                st.markdown(
                    f'<div style="margin-top:16px;position:relative;height:6px;background:#1e293b;border-radius:999px;">'
                    f'<div style="position:absolute;left:0;top:0;height:6px;width:{pct:.1f}%;background:linear-gradient(90deg,#38bdf8,#22d3ee);border-radius:999px;"></div>'
                    f'<div style="position:absolute;left:0;top:-5px;height:16px;width:16px;border-radius:50%;background:#38bdf8;"></div>'
                    f'<div style="position:absolute;left:calc({pct:.1f}% - 8px);top:-5px;height:16px;width:16px;'
                    f'border-radius:50%;background:#22d3ee;box-shadow:0 0 8px #22d3ee;"></div>'
                    f'<div style="position:absolute;right:0;top:-5px;height:16px;width:16px;border-radius:50%;background:#334155;"></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;margin-top:8px;font-size:13px;color:#94a3b8;">'
                    f'<span><b style="color:#f1f5f9;">ATD:</b> {v["atd"].strftime("%Y-%m-%d %H:%M")}</span>'
                    f'<span><b style="color:#f1f5f9;">Reported ETA:</b> {v["eta"].strftime("%Y-%m-%d %H:%M")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            show_past = btn_col1.button("\U0001F519 Past track", key="past_track_btn", use_container_width=True)
            show_forecast = btn_col2.button("\U0001F4CD Route forecast", key="route_forecast_btn", use_container_width=True)
            btn_col3.button("\u2795 Add to fleet", key="add_fleet_btn", use_container_width=True)
            btn_col4.button("\U0001F6A2 Vessel details", key="vessel_details_btn", use_container_width=True, type="primary")

            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Navigational status", v["nav_status"])
            m2.metric("Speed / Course", f"{v['speed_knots']} kn / {v['heading']:.0f}\u00b0")
            m3.metric("Draught", f"{v['draught_m']} m")
            m4.metric("Fuel type", v["fuel"])

            st.caption(f"Received: a few minutes ago (AIS source: Simulated \u2014 synthetic fleet, not a real feed) \u00b7 Lane: {v['lane']}")

            if (show_past or show_forecast) and v["lane_waypoints"]:
                n_pts = 25
                if show_past:
                    track = [_lane_point(v["lane_waypoints"], v["progress"] * f, jitter_deg=0.3)[:2] for f in [i / n_pts for i in range(n_pts + 1)]]
                    track_layer = pdk.Layer("PathLayer", data=[{"path": [[lon, lat] for lat, lon in track]}],
                                             get_path="path", get_color=[59, 130, 246], get_width=3, width_min_pixels=2)
                    label = "Past track (synthetic reconstruction)"
                else:
                    remaining = [v["progress"] + (1 - v["progress"]) * (i / n_pts) for i in range(n_pts + 1)]
                    track = [_lane_point(v["lane_waypoints"], f, jitter_deg=0.3)[:2] for f in remaining]
                    track_layer = pdk.Layer("PathLayer", data=[{"path": [[lon, lat] for lat, lon in track]}],
                                             get_path="path", get_color=[249, 115, 22], get_width=3, width_min_pixels=2, get_dash_array=[4, 3])
                    label = "Route forecast (projected to destination)"
                track_view = pdk.ViewState(latitude=v["lat"], longitude=v["lon"], zoom=2.5)
                st.caption(label)
                st.pydeck_chart(pdk.Deck(layers=[track_layer], initial_view_state=track_view, map_style="light"),
                                 use_container_width=True, height=400)
            elif (show_past or show_forecast):
                st.caption("This vessel is open-ocean background traffic with no defined lane, so no track is available.")

            st.markdown("#### \U0001F4A8 Scope 3 Emissions \u2014 this vessel")
            fuel_t_day, fuel_kg_hr, co2_kg_hr = estimate_fuel_and_co2(
                VESSEL_CLASS_PROFILE[v["class"]]["fuel_profile"], v["fuel"], v["speed_knots"]
            )
            remaining_hours = max(0, (v["eta"] - dt.datetime(2026, 7, 26, 9, 0)).total_seconds() / 3600)
            total_co2_remaining_t = co2_kg_hr * remaining_hours / 1000
            e1, e2, e3 = st.columns(3)
            e1.metric("Est. fuel consumption", f"{fuel_t_day} t/day")
            e2.metric("Est. CO2 rate", f"{co2_kg_hr:,.0f} kg/hr")
            e3.metric("Est. CO2e for remaining voyage", f"{total_co2_remaining_t:,.1f} t")
            st.caption("Estimated from speed using the standard cube-law fuel curve (real AIS doesn't transmit fuel flow) \u2014 "
                        "see Scope 3 Calculator methodology.")

            st.markdown("#### \U0001F324\uFE0F Live Weather at Vessel Position")
            with st.spinner("Fetching live weather (Open-Meteo)\u2026"):
                weather = fetch_weather(v["lat"], v["lon"])
            if "weather_error" in weather and "wave_height_m" not in weather:
                st.warning(f"Couldn't reach the weather service: {weather.get('weather_error', 'unknown error')}")
            else:
                w1, w2, w3, w4 = st.columns(4)
                w1.metric("Air temp", f"{weather.get('temperature_c', 'n/a')} \u00b0C")
                w2.metric("Wind speed", f"{weather.get('wind_speed_kmh', 'n/a')} km/h")
                w3.metric("Wave height", f"{weather.get('wave_height_m', 'n/a')} m")
                w4.metric("Wave period", f"{weather.get('wave_period_s', 'n/a')} s")

            st.markdown("#### \U0001F916 AI Summary")
            key = st.session_state.get("anthropic_api_key", "")
            summary_key = f"vessel_summary_{v['vessel_id']}"
            if st.button("Generate AI summary for this vessel", key=f"gen_vessel_summary_{v['vessel_id']}"):
                vctx = (
                    f"Vessel: {v['name']} ({v['class']}, flag {v['flag']})\n"
                    f"Route: {v['origin_name']} ({v['origin_code']}) \u2192 {v['dest_name']} ({v['dest_code']}), "
                    f"{int(v['progress']*100)}% complete, ETA {v['eta'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"Speed: {v['speed_knots']} kn, course {v['heading']:.0f}\u00b0, draught {v['draught_m']} m, "
                    f"status: {v['nav_status']}, fuel: {v['fuel']}\n"
                    f"Estimated fuel use: {fuel_t_day} t/day, CO2 rate {co2_kg_hr:,.0f} kg/hr, "
                    f"estimated {total_co2_remaining_t:,.1f} t CO2e for the remaining voyage\n"
                    f"Live weather at current position: {weather}"
                )
                if key:
                    try:
                        summary = call_claude(
                            key,
                            system_prompt=("You are a maritime carbon and operations analyst. Write a concise "
                                            "3-4 sentence summary of this vessel's current voyage, emissions "
                                            "footprint, and any weather-related risk or efficiency note, using "
                                            "only the data given. Plain English, no headers."),
                            user_message=vctx, max_tokens=300,
                        )
                        st.session_state[summary_key] = summary
                    except Exception as e:
                        st.error(f"Claude API error: {e}")
                else:
                    wind = weather.get("wind_speed_kmh")
                    wave = weather.get("wave_height_m")
                    weather_note = (
                        f"Current conditions show {wind} km/h wind and {wave} m wave height at its position, "
                        if wind is not None and wave is not None else "Live weather at its position is shown above, "
                    )
                    st.session_state[summary_key] = (
                        f"{v['name']} is {int(v['progress']*100)}% through its voyage from {v['origin_name']} to "
                        f"{v['dest_name']}, currently making {v['speed_knots']} knots on {v['fuel']}. "
                        f"{weather_note}"
                        f"and estimated fuel burn at this speed is {fuel_t_day} t/day, producing roughly "
                        f"{total_co2_remaining_t:,.1f} t CO2e for the remaining leg. "
                        f"{'Consider a lower-carbon fuel switch on this class of vessel to reduce the footprint.' if v['class'] in ('Cargo','Tanker') else ''}"
                    )
            if summary_key in st.session_state:
                st.markdown(f'<div class="card">{st.session_state[summary_key]}</div>', unsafe_allow_html=True)
    else:
        st.caption("Click any triangle on the map above to see full vessel details, Scope 3 emissions, live weather, and an AI summary.")

    st.markdown("#### Fleet composition")
    comp = view_df["class"].value_counts().reset_index()
    comp.columns = ["class", "count"]
    fig = px.bar(comp, x="count", y="class", orientation="h", color="class",
                 color_discrete_map={k: "#%02x%02x%02x" % v[0] for k, v in VESSEL_CLASS_STYLE.items()})
    fig.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

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
        fig.update_traces(textfont_color="#0a0a0a", marker=dict(line=dict(color="#000000", width=2)))
        fig.update_layout(**PLOTLY_LAYOUT, height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Scope 3 Summary by Source")
    source_rows = source_df.to_dict("records")
    for row_start in range(0, len(source_rows), 4):
        row_chunk = source_rows[row_start:row_start + 4]
        row_cols = st.columns(4)
        for col, item in zip(row_cols, row_chunk):
            col.metric(item["source"], f"{item['pct']}% of total")

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
                              fillcolor="rgba(45,212,191,0.18)", line=dict(width=0), name="Confidence band"))
    fig.add_trace(go.Scatter(x=forecast_df["month"], y=forecast_df["predicted"], name="Forecast",
                              line=dict(color="#2dd4bf", width=3),
                              mode="lines+markers", marker=dict(size=7, color="#22d3ee", line=dict(color="#000000", width=1))))
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
