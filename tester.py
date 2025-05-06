import pandas as pd
import geopandas as gpd
import folium
from branca.colormap import linear
from folium.features import GeoJsonTooltip
import webbrowser
import os

# --- Load and clean walkability dataset ---
print("📂 Loading walkability data...")
df = pd.read_csv("walkability_fixed_sample.csv")
print("🔎 Columns in walkability data:", df.columns)
print(df.head())

# Ensure GEOID10 is string and correctly 11 characters (not accidentally 12)
df["GEOID10"] = df["GEOID10"].astype(str).str.zfill(11).str[-11:]
print("🧪 Sample GEOIDs:", df["GEOID10"].unique())

# --- Load shapefile and clean GEOID ---
wa_tracts = gpd.read_file("tl_2021_53_tract.zip")
print("🗺 Columns in shapefile:", wa_tracts.columns)

# Ensure GEOID is also a string
wa_tracts["GEOID"] = wa_tracts["GEOID"].astype(str).str.zfill(11)

# --- Match and merge ---
merged = wa_tracts.merge(df, left_on="GEOID", right_on="GEOID10", how="left")

# Diagnostics
print("📌 Sample GEOIDs from shapefile:", wa_tracts["GEOID"].head().tolist())
print("📌 Sample GEOIDs from CSV:", df["GEOID10"].head().tolist())
matched_geoids = df["GEOID10"].isin(wa_tracts["GEOID"]).sum()
print(f"✅ Matched GEOIDs: {matched_geoids} of {len(df)} in walkability data")

# --- Check for nulls ---
print("\n📉 Null values after merge:")
print(merged[["NatWalkInd", "TotPop", "TotEmp", "D1A"]].isnull().sum())

# --- Prepare for mapping ---
merged = merged.to_crs(epsg=4326)
merged["geometry"] = merged["geometry"].simplify(0.001, preserve_topology=True)

mean_lat = merged.geometry.centroid.y.mean()
mean_lon = merged.geometry.centroid.x.mean()

# Create folium map
m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7, tiles="cartodbpositron")

# Color scale based on actual values in merged
walk_values = merged["NatWalkInd"].dropna()
min_walk, max_walk = walk_values.min(), walk_values.max()
print(f"✅ Walkability index range: {min_walk} to {max_walk}")

colormap = linear.YlGnBu_09.scale(min_walk, max_walk)
colormap.caption = 'National Walkability Index'
colormap.add_to(m)

# Add Choropleth (USE GEOID — NOT GEOID10)
folium.Choropleth(
    geo_data=merged,
    data=merged,
    columns=["GEOID", "NatWalkInd"],
    key_on="feature.properties.GEOID",
    fill_color="YlGnBu",
    fill_opacity=0.7,
    line_opacity=0.2,
    nan_fill_color="gray",
    legend_name="National Walkability Index"
).add_to(m)

# Tooltip configuration
tooltip = GeoJsonTooltip(
    fields=["GEOID", "NatWalkInd", "TotPop", "TotEmp", "D1A"],
    aliases=["Tract ID:", "Walkability Index:", "Total Population:", "Total Employment:", "Density (D1A):"],
    localize=True,
    sticky=False,
    labels=True,
    style=("background-color: white; color: #333333; font-family: Arial; font-size: 12px; padding: 6px;")
)

# Add GeoJson layer with tooltip
folium.GeoJson(
    merged,
    name="Census Tracts",
    style_function=lambda x: {"fillOpacity": 0, "color": "black", "weight": 0.3},
    highlight_function=lambda x: {"fillOpacity": 0.1, "color": "blue", "weight": 1},
    tooltip=tooltip
).add_to(m)

# Finalize and open map
map_path = "washington_walkability_map.html"
m.save(map_path)
print(f"✅ Map saved as {map_path}")
webbrowser.open("file://" + os.path.realpath(map_path))
