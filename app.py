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
# Theme (black background, high-contrast text)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #000000; color: #f1f5f9; }
    section[data-testid="stSidebar"] { background-color: #050505; }
    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    h1 {
        background: linear-gradient(90deg, #22d3ee, #2dd4bf);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    h2, h3 { color: #ffffff !important; }
    p, .stMarkdown, .stCaption, label { color: #e2e8f0 !important; }
    div[data-testid="stMetric"] {
        background: #0d0d0d;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] { color: #7dd3fc !important; white-space: normal !important; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    .badge {
        display:inline-block; padding:2px 10px; border-radius:999px;
        font-size:11px; font-weight:600;
    }
    .badge-low{background:rgba(52,211,153,.15); color:#34d399;}
    .badge-med{background:rgba(251,191,36,.15); color:#fbbf24;}
    .badge-high{background:rgba(248,113,113,.15); color:#f87171;}
    .card {
        background: #0d0d0d;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PALETTE = ["#38bdf8", "#2dd4bf", "#34d399", "#fbbf24", "#a78bfa", "#f87171", "#fb923c", "#94a3b8"]
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
# Synthetic data generation
# ---------------------------------------------------------------------------
@st.cache_data
def gen_vessels(n=8):
    rows = []
    for i in range(n):
        dest = GLOBAL_DESTS.iloc[i % len(GLOBAL_DESTS)]
        origin_port = PORTS[PORTS["kind"] == "port"].sample(1, random_state=i).iloc[0]
        progress = round(random.uniform(0.05, 0.85), 2)
        speed = round(random.uniform(11, 20), 1)
        rows.append({
            "name": f"{random.choice(VESSEL_PREFIX)} {random.choice(VESSEL_NAMES)}",
            "type": random.choice(VESSEL_TYPES),
            "fuel": random.choice(FUEL_TYPES),
            "origin_id": origin_port["id"], "origin_name": origin_port["name"],
            "origin_lat": origin_port["lat"], "origin_lon": origin_port["lon"],
            "dest_id": dest["id"], "dest_name": dest["name"],
            "dest_lat": dest["lat"], "dest_lon": dest["lon"],
            "progress": progress,
            "speed_knots": speed,
            "eta_hours": round((1 - progress) * random.uniform(60, 260), 1),
            "co2e_tonnes": round(random.uniform(80, 480), 1),
        })
    return pd.DataFrame(rows)


def interpolate_position(o_lat, o_lon, d_lat, d_lon, t):
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
    ["Dashboard", "Singapore Map", "Scope 3 Calculator", "Live Vessel Tracking",
     "Live Truck Tracking", "Predictive Analytics", "AI Carbon Copilot", "Reports"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption("Live data \u00b7 synthetic demo dataset")

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
        name="Satellite", overlay=False, control=True,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Esri labels", name="Labels", overlay=True, control=True,
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
    c1.metric("Total Scope 3 Emissions", "112.0K t CO2e", "-2.6%")
    c2.metric("Monthly Emissions", f"{monthly_df.iloc[-1]['total']:,} t CO2e", "+3.4%")
    c3.metric("Active Shipments", "480", "+1.9%")
    c4.metric("MPA Green Score", "79 / 100", "+2.5%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Vessels Tracked", str(len(vessels_df)))
    c6.metric("Trucks Tracked", str(len(trucks_df)))
    c7.metric("Carbon Reduction", "11.8%", "+1.4%")
    c8.metric("Avg CO2e / Shipment", "241 kg", "-2.1%")

    st.markdown("### Monthly Emissions Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["budget"], name="Budget",
                              line=dict(color="#fbbf24", dash="dash")))
    fig.add_trace(go.Scatter(x=monthly_df["month"], y=monthly_df["total"], name="Actual",
                              line=dict(color="#38bdf8", width=3), fill="tozeroy",
                              fillcolor="rgba(56,189,248,0.15)"))
    fig.update_layout(**PLOTLY_LAYOUT, height=300)
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Emissions by Source")
        fig2 = px.bar(source_df.sort_values("pct"), x="pct", y="source", orientation="h",
                       color="source", color_discrete_sequence=PALETTE)
        fig2.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        st.markdown("### Top Emitting Export Lanes")
        fig3 = px.bar(routes_df.sort_values("co2e"), x="co2e", y="route", orientation="h",
                       color="route", color_discrete_sequence=PALETTE)
        fig3.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### Singapore Network Map")
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
    st.caption(f"{len(vessels_df)} vessels tracked, all outbound from Singapore \u00b7 satellite view")

    m = build_satellite_map(center=(10, 90), zoom=3)
    for _, p in PORTS[PORTS["kind"] == "port"].iterrows():
        folium.CircleMarker([p["lat"], p["lon"]], radius=6, color="cadetblue", fill=True, fill_opacity=0.9,
                             popup=p["name"]).add_to(m)
    for _, v in vessels_df.iterrows():
        pts = [interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], t / 20)
               for t in range(21)]
        folium.PolyLine(pts, color="#38bdf8", weight=1.5, opacity=0.6, dash_array="2,6").add_to(m)
        lat, lon = interpolate_position(v["origin_lat"], v["origin_lon"], v["dest_lat"], v["dest_lon"], v["progress"])
        folium.CircleMarker([lat, lon], radius=6, color="#0ea5e9", fill=True, fill_opacity=0.95,
                             popup=f"<b>{v['name']}</b><br>{v['type']} \u00b7 {v['fuel']}<br>"
                                   f"To: {v['dest_name']}<br>Speed: {v['speed_knots']} kn \u00b7 ETA {v['eta_hours']}h").add_to(m)
    st_folium(m, height=460, use_container_width=True, key="vessel_map")

    st.markdown("### Fleet")
    for _, v in vessels_df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        col1.markdown(f"**{v['name']}**  \n{v['type']} \u2192 {v['dest_name']} ({v['fuel']})")
        col2.metric("Speed", f"{v['speed_knots']} kn")
        col3.metric("ETA", f"{v['eta_hours']} h")
        col4.metric("CO2e", f"{v['co2e_tonnes']} t")
        col5.progress(v["progress"], text=f"{int(v['progress']*100)}%")

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
                              line=dict(color="#2dd4bf", width=3), mode="lines+markers"))
    fig.update_layout(**PLOTLY_LAYOUT, height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(forecast_df, hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Page: AI Carbon Copilot
# ---------------------------------------------------------------------------
elif page == "AI Carbon Copilot":
    st.title("AI Carbon Copilot")
    st.caption("Grounded in Singapore Scope 3 shipment, supplier, and route data")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi, I'm the Marcura Carbon Copilot, scoped to Singapore operations. "
                                              "Ask me about Tuas Port, Jurong Island, suppliers, or reduction opportunities."}
        ]

    def reply(q):
        s = q.lower()
        last_total = int(monthly_df.iloc[-1]["total"])
        last_budget = int(monthly_df.iloc[-1]["budget"])
        if "emission" in s and ("month" in s or "total" in s):
            return f"Last month, Singapore operations emitted {last_total:,} t CO2e against a budget of {last_budget:,} t."
        if "supplier" in s:
            return "Jurong Petrochemical Supplies Pte Ltd has the highest YTD footprint at 6,240 t CO2e, flagged High risk given Jurong Island's energy intensity."
        if "tuas" in s:
            return "Tuas Port emissions are up 9% this month as mega-port throughput ramps up \u2014 this is expected during the phased handover from Pasir Panjang."
        if "route" in s or "lane" in s:
            return "The highest-emitting lane is Tuas Port \u2192 Rotterdam at 3,120 t CO2e. LNG-fueled vessel substitution could cut this lane's footprint by roughly 9%."
        if "reduc" in s:
            return "Top levers for Singapore ops: shift Jurong Island bunkering to LNG, consolidate Jurong-to-Tuas road freight, and route more Changi air cargo via sea-air through Pasir Panjang."
        return f"This month's Singapore Scope 3 emissions are {last_total:,} t CO2e. Ask me about Tuas Port, Jurong Island, a specific supplier, or a shipping lane."

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    suggestions = ["What were emissions last month?", "Why are Tuas Port emissions up?", "Which supplier has the highest footprint?"]
    cols = st.columns(len(suggestions))
    clicked = None
    for i, s in enumerate(suggestions):
        if cols[i].button(s, key=f"sugg_{i}"):
            clicked = s

    user_input = st.chat_input("Ask about Tuas, Jurong Island, suppliers\u2026") or clicked
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
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
