import streamlit as st
import boto3
import rasterio
from rasterio.session import AWSSession
from rasterio.plot import show
import folium
from streamlit_folium import st_folium
import numpy as np
import matplotlib.pyplot as plt
import io

# AWS Configuration (Set your own credentials or use IAM roles)
AWS_ACCESS_KEY = "AKIA5D4NBVNJUZ7VFGJ4"
AWS_SECRET_KEY = "vv5CpKzjKyuSiHw/RzI88TCQb1hezwrrtyrvVtWJ"
AWS_BUCKET_NAME = "euspa"



# Create an S3 client
session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)
s3_client = session.client('s3')

# List available COG files in the S3 bucket
def list_cog_files(bucket_name):
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    cog_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith(".tif")]
    return cog_files

cog_files = list_cog_files(AWS_BUCKET_NAME)

# Streamlit UI
st.title("Water Depth Visualization from COG Files")
st.sidebar.header("Controls")

# Let user select a COG file from the available list
selected_cog = st.sidebar.selectbox("Select Water Depth Map", cog_files)

# Display a time-step slider (assuming different COGs correspond to different time steps)
time_step = st.sidebar.slider("Select Time Step", 0, len(cog_files) - 1, 0)

# Read selected COG from S3 and process it
def load_cog_from_s3(bucket, cog_key):
    """Loads a Cloud Optimized GeoTIFF (COG) from an S3 bucket"""
    s3_url = f"/vsis3/{bucket}/{cog_key}"
    session = AWSSession(session)
    with rasterio.Env(session):
        with rasterio.open(s3_url) as src:
            data = src.read(1)
            profile = src.profile
    return data, profile

# Load selected COG
cog_data, cog_profile = load_cog_from_s3(AWS_BUCKET_NAME, selected_cog)

# Create a colormap legend
def create_color_legend():
    fig, ax = plt.subplots(figsize=(6, 1))
    cmap = plt.get_cmap("Blues")
    norm = plt.Normalize(vmin=np.min(cog_data), vmax=np.max(cog_data))
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    ax.set_title("Water Depth (m)")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    st.sidebar.image(buf)

create_color_legend()

# Generate Map with Folium and MapLibre
m = folium.Map(location=[37.5, 35.5], zoom_start=6, tiles="https://api.maptiler.com/maps/streets/{z}/{x}/{y}.png?key=your-maptiler-key", attr="MapTiler")

# Overlay COG data as an image on the map
cog_bounds = [[cog_profile['bounds'].bottom, cog_profile['bounds'].left], [cog_profile['bounds'].top, cog_profile['bounds'].right]]
folium.raster_layers.ImageOverlay(
    image=cog_data,
    bounds=cog_bounds,
    opacity=0.6,
    colormap=lambda x: (0, 0, x, x),
).add_to(m)

# Display map in Streamlit
st_folium(m, width=800, height=600)

# Allow user to inspect water depth at clicked location
st.sidebar.header("Inspect Water Depth")
st.write("Click on the map to get water depth value.")

if "clicked_point" in st.session_state:
    lat, lon = st.session_state["clicked_point"]
    with rasterio.open(f"/vsis3/{AWS_BUCKET_NAME}/{selected_cog}") as src:
        row, col = src.index(lon, lat)
        water_depth = src.read(1)[row, col]
        st.sidebar.write(f"Depth at ({lat:.4f}, {lon:.4f}): {water_depth:.2f} meters")
