"""
Marcura Scope 3 Intelligence - Synthetic Data Generator
Generates fictional demo data for Singapore Hub and Dubai Hub.
NOTE: All data is synthetic / fictional. No real company or shipment data.
"""
import json
import random
import math
from datetime import datetime, timedelta

random.seed(42)

OUT = "../data"

# ---------------------------------------------------------------------
# Reference geo anchors
# ---------------------------------------------------------------------
SG_ANCHOR = (1.2644, 103.8200)   # PSA Singapore
DXB_ANCHOR = (25.0161, 55.0614)  # Jebel Ali

SG_ROUTES = [
    {"name": "Singapore - Shanghai", "start": (1.2644, 103.8200), "end": (31.2304, 121.4737)},
    {"name": "Singapore - Rotterdam", "start": (1.2644, 103.8200), "end": (51.9481, 4.1428)},
    {"name": "Singapore - Port Klang", "start": (1.2644, 103.8200), "end": (3.0000, 101.3900)},
    {"name": "Singapore - Ho Chi Minh", "start": (1.2644, 103.8200), "end": (10.7626, 106.6602)},
    {"name": "Singapore - Colombo", "start": (1.2644, 103.8200), "end": (6.9271, 79.8612)},
    {"name": "Singapore - Jakarta (Tanjung Priok)", "start": (1.2644, 103.8200), "end": (-6.1045, 106.8811)},
    {"name": "Singapore - Manila", "start": (1.2644, 103.8200), "end": (14.5833, 120.9667)},
    {"name": "Singapore - Fremantle", "start": (1.2644, 103.8200), "end": (-32.0569, 115.7439)},
]

DXB_ROUTES = [
    {"name": "Jebel Ali - Jeddah", "start": (25.0161, 55.0614), "end": (21.4858, 39.1925)},
    {"name": "Jebel Ali - Karachi", "start": (25.0161, 55.0614), "end": (24.8546, 66.9988)},
    {"name": "Jebel Ali - Mundra", "start": (25.0161, 55.0614), "end": (22.8394, 69.7220)},
    {"name": "Jebel Ali - Salalah", "start": (25.0161, 55.0614), "end": (17.0151, 54.0924)},
    {"name": "Jebel Ali - Suez", "start": (25.0161, 55.0614), "end": (29.9668, 32.5498)},
    {"name": "Jebel Ali - Basra (Umm Qasr)", "start": (25.0161, 55.0614), "end": (30.0333, 47.9167)},
    {"name": "Jebel Ali - Doha (Hamad)", "start": (25.0161, 55.0614), "end": (25.0000, 51.6000)},
    {"name": "Jebel Ali - Mombasa", "start": (25.0161, 55.0614), "end": (-4.0435, 39.6682)},
]

VESSEL_TYPES = ["Container Ship", "Bulk Carrier", "Tanker", "RoRo", "Feeder Vessel"]
SG_SUPPLIER_SECTORS = ["Electronics Components", "Precision Manufacturing", "Semiconductor Assembly",
                       "Packaging & Logistics", "Marine Bunkering", "Cold Chain Logistics"]
DXB_SUPPLIER_SECTORS = ["Steel & Metals", "Building Materials", "Oil Field Equipment",
                        "FMCG Distribution", "Chemicals", "Textiles & Apparel"]

FICTIONAL_SUPPLIER_NAMES = [
    "Novasea Trading Co.", "Orion Maritime Supplies", "Falcon Ridge Industries",
    "BlueHarbor Components", "Crescent Bay Logistics", "Zenith Freightworks",
    "Meridian Cargo Partners", "Silverline Manufacturing", "Coral Strait Exporters",
    "Amberly Global Sourcing", "Palmgate Distribution", "TransArc Suppliers",
    "Ironvale Steelworks", "Sundew Chemicals Ltd.", "Northstar Textiles",
    "Harborlight Electronics", "Windrose Packaging", "Deltafresh Cold Chain",
    "Anchorpoint Trading", "Lumen Precision Parts",
]

def haversine_interp(p1, p2, frac):
    lat = p1[0] + (p2[0] - p1[0]) * frac
    lon = p1[1] + (p2[1] - p1[1]) * frac
    return lat, lon

def gen_vessels(routes, n=24, prefix="SG"):
    vessels = []
    for i in range(n):
        route = random.choice(routes)
        frac = random.random()
        lat, lon = haversine_interp(route["start"], route["end"], frac)
        # jitter to simulate real track noise
        lat += random.uniform(-0.4, 0.4)
        lon += random.uniform(-0.4, 0.4)
        speed = round(random.uniform(8.0, 22.5), 1)
        heading = round(random.uniform(0, 359), 0)
        status = random.choices(
            ["Underway", "At Anchor", "Moored", "Delayed"],
            weights=[0.55, 0.2, 0.15, 0.10]
        )[0]
        if status in ("At Anchor", "Moored"):
            speed = round(random.uniform(0, 1.2), 1)
        eta_hours = round(random.uniform(4, 96), 1)
        vessels.append({
            "vessel_id": f"{prefix}-VSL-{1000+i}",
            "vessel_name": f"MV {random.choice(['Pacific','Atlantic','Coral','Amber','Northern','Silver','Golden','Emerald'])} {random.choice(['Trader','Voyager','Express','Star','Horizon','Pioneer'])}",
            "type": random.choice(VESSEL_TYPES),
            "route": route["name"],
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "speed_knots": speed,
            "heading_deg": heading,
            "status": status,
            "eta_hours": eta_hours,
            "co2_tonnes_voyage": round(random.uniform(150, 4200), 1),
            "fuel_type": random.choice(["VLSFO", "MGO", "LNG", "Biofuel Blend"]),
        })
    return vessels

def gen_route_tracks(routes, points_per_route=12, prefix="SG"):
    tracks = []
    for r_idx, route in enumerate(routes):
        pts = []
        for p in range(points_per_route + 1):
            frac = p / points_per_route
            lat, lon = haversine_interp(route["start"], route["end"], frac)
            lat += random.uniform(-0.15, 0.15)
            lon += random.uniform(-0.15, 0.15)
            pts.append([round(lon, 4), round(lat, 4)])
        tracks.append({
            "route_id": f"{prefix}-RT-{r_idx+1}",
            "name": route["name"],
            "path": pts,
            "avg_transit_days": round(random.uniform(3, 22), 1),
            "monthly_shipments": random.randint(8, 65),
            "co2_intensity_kg_per_teu": round(random.uniform(45, 180), 1),
        })
    return tracks

def gen_suppliers(sectors, prefix, n=20):
    suppliers = []
    names = FICTIONAL_SUPPLIER_NAMES.copy()
    random.shuffle(names)
    for i in range(n):
        esg = round(random.uniform(38, 96), 1)
        suppliers.append({
            "supplier_id": f"{prefix}-SUP-{200+i}",
            "name": names[i % len(names)] + (f" ({prefix})" if i >= len(names) else ""),
            "sector": random.choice(sectors),
            "esg_score": esg,
            "esg_tier": "Leading" if esg >= 80 else "Developing" if esg >= 60 else "At Risk",
            "scope3_emissions_tco2e": round(random.uniform(120, 9800), 1),
            "spend_usd": round(random.uniform(50000, 4200000), 0),
            "active_pos": random.randint(2, 48),
            "on_time_delivery_pct": round(random.uniform(72, 99.5), 1),
            "country": random.choice(["China", "Vietnam", "India", "Malaysia", "Indonesia", "South Korea"]) if prefix == "SG"
                       else random.choice(["India", "Saudi Arabia", "Pakistan", "Oman", "Egypt", "Turkey"]),
        })
    return suppliers

def gen_emissions_timeseries(months=18, base=42000, seed_offset=0):
    series = []
    d = datetime(2025, 2, 1)
    val = base
    for m in range(months):
        val = max(base * 0.6, val + random.uniform(-2500, 1800) - seed_offset * 30)
        series.append({
            "month": (d + timedelta(days=30*m)).strftime("%Y-%m"),
            "scope3_tco2e": round(val, 1),
            "transport_pct": round(random.uniform(38, 52), 1),
            "procurement_pct": round(random.uniform(28, 40), 1),
            "packaging_pct": round(random.uniform(5, 12), 1),
            "other_pct": round(random.uniform(4, 10), 1),
        })
    return series

def gen_shipments(prefix, n=40):
    shipments = []
    for i in range(n):
        delay = random.choices([0, 1, 2, 3], weights=[0.6, 0.2, 0.12, 0.08])[0]
        shipments.append({
            "shipment_id": f"{prefix}-SHP-{5000+i}",
            "origin": random.choice(["Shanghai", "Ningbo", "Shenzhen", "Busan"]) if prefix == "SG"
                      else random.choice(["Mumbai", "Jeddah", "Karachi", "Mundra"]),
            "destination": "Singapore (PSA/Tuas)" if prefix == "SG" else "Jebel Ali (JAFZA)",
            "container_teu": random.randint(1, 6),
            "status": random.choices(["In Transit", "At Port", "Cleared", "Delayed"], weights=[0.4,0.25,0.25,0.10])[0],
            "delay_days": delay,
            "dwell_time_hours": round(random.uniform(6, 96), 1),
            "co2_kg": round(random.uniform(400, 18000), 1),
            "value_usd": round(random.uniform(8000, 620000), 0),
        })
    return shipments

def gen_ai_insights(prefix):
    if prefix == "SG":
        return [
            {"title": "Route consolidation opportunity", "detail": "Consolidating Singapore–Colombo feeder calls could cut transshipment CO2 by an estimated 11% per TEU.", "impact": "High", "category": "Route Optimization"},
            {"title": "Vessel turnaround improvement", "detail": "Average PSA berth dwell time is 18% above ASEAN benchmark for electronics cargo; digital twin suggests re-sequencing crane allocation.", "impact": "Medium", "category": "Port Operations"},
            {"title": "Supplier decarbonization candidate", "detail": "3 electronics suppliers in Shenzhen show ESG tier 'Developing' with high Scope 3 intensity — recommend engagement program.", "impact": "High", "category": "Supplier ESG"},
            {"title": "Predictive delay alert", "detail": "Monsoon-linked congestion risk flagged for Ho Chi Minh route in the next 10 days.", "impact": "Medium", "category": "Risk"},
        ]
    return [
        {"title": "Sea-air corridor opportunity", "detail": "Shifting 15% of Jeddah-origin urgent cargo to sea-air via Dubai South could reduce lead time by 4 days at comparable emissions cost.", "impact": "High", "category": "Procurement"},
        {"title": "Supplier ESG gap", "detail": "Steel & Metals suppliers account for 34% of Dubai hub Scope 3 emissions despite only 19% of spend — priority for engagement.", "impact": "High", "category": "Supplier ESG"},
        {"title": "PO consolidation", "detail": "Consolidating purchase orders across 4 GCC distribution suppliers could reduce shipment count by ~22% without inventory risk.", "impact": "Medium", "category": "Procurement"},
        {"title": "Predictive delay alert", "detail": "Red Sea corridor risk flagged — reroute contingency via Cape recommended for 2 active shipments.", "impact": "High", "category": "Risk"},
    ]

def build_hub(prefix, routes, sectors, out_dir):
    vessels = gen_vessels(routes, n=26, prefix=prefix)
    tracks = gen_route_tracks(routes, prefix=prefix)
    suppliers = gen_suppliers(sectors, prefix, n=20)
    emissions = gen_emissions_timeseries(seed_offset=0 if prefix == "SG" else 1)
    shipments = gen_shipments(prefix, n=40)
    insights = gen_ai_insights(prefix)

    total_emissions = sum(s["scope3_emissions_tco2e"] for s in suppliers)
    total_spend = sum(s["spend_usd"] for s in suppliers)

    exec_summary = {
        "hub": "Singapore" if prefix == "SG" else "Dubai",
        "total_scope3_tco2e": round(total_emissions, 1),
        "total_procurement_spend_usd": round(total_spend, 0),
        "active_suppliers": len(suppliers),
        "shipments_monitored": len(shipments),
        "vessels_tracked": len(vessels),
        "carbon_reduction_opportunities": len(insights),
        "primary_hotspot": "Transshipment" if prefix == "SG" else "Procurement",
        "main_opportunity": "Route optimization" if prefix == "SG" else "Supplier decarbonization",
    }

    with open(f"{out_dir}/vessels.json", "w") as f: json.dump(vessels, f, indent=2)
    with open(f"{out_dir}/routes.json", "w") as f: json.dump(tracks, f, indent=2)
    with open(f"{out_dir}/suppliers.json", "w") as f: json.dump(suppliers, f, indent=2)
    with open(f"{out_dir}/emissions.json", "w") as f: json.dump(emissions, f, indent=2)
    with open(f"{out_dir}/shipments.json", "w") as f: json.dump(shipments, f, indent=2)
    with open(f"{out_dir}/ai-insights.json", "w") as f: json.dump(insights, f, indent=2)
    with open(f"{out_dir}/executive-summary.json", "w") as f: json.dump(exec_summary, f, indent=2)

    return exec_summary

if __name__ == "__main__":
    import os
    sg_dir = os.path.join(os.path.dirname(__file__), OUT, "singapore")
    dxb_dir = os.path.join(os.path.dirname(__file__), OUT, "dubai")
    os.makedirs(sg_dir, exist_ok=True)
    os.makedirs(dxb_dir, exist_ok=True)

    sg_summary = build_hub("SG", SG_ROUTES, SG_SUPPLIER_SECTORS, sg_dir)
    dxb_summary = build_hub("DXB", DXB_ROUTES, DXB_SUPPLIER_SECTORS, dxb_dir)

    global_summary = {
        "global_scope3_tco2e": round(sg_summary["total_scope3_tco2e"] + dxb_summary["total_scope3_tco2e"], 1),
        "total_procurement_spend_usd": round(sg_summary["total_procurement_spend_usd"] + dxb_summary["total_procurement_spend_usd"], 0),
        "active_suppliers": sg_summary["active_suppliers"] + dxb_summary["active_suppliers"],
        "shipments_monitored": sg_summary["shipments_monitored"] + dxb_summary["shipments_monitored"],
        "carbon_reduction_opportunities": sg_summary["carbon_reduction_opportunities"] + dxb_summary["carbon_reduction_opportunities"],
        "singapore": sg_summary,
        "dubai": dxb_summary,
    }
    with open(os.path.join(os.path.dirname(__file__), OUT, "global-summary.json"), "w") as f:
        json.dump(global_summary, f, indent=2)

    print("Data generation complete.")
    print(json.dumps(global_summary, indent=2))
