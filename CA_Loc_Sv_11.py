# File: ca_loc_sv_app.py

import streamlit as st
import pandas as pd
import requests
import math
import os
import io
import zipfile

# Constants
API_KEY = 'AIzaSyDNdt-Um0cSjqNYQQBZwfdvdkHAUKMsqOI'  # Replace 'YOUR_API_KEY' with your actual API key
STREET_VIEW_URL = 'https://maps.googleapis.com/maps/api/streetview'
METADATA_URL = 'https://maps.googleapis.com/maps/api/streetview/metadata'
DEFAULT_VIEW_TYPE = 'RV'  # Default view type is Road View

def get_panorama_metadata(lat, lon, view_type):
    params = {
        'location': f'{lat},{lon}',
        'key': API_KEY
    }
    if view_type == 'FV':
        params['source'] = 'outdoor'  # Optionally set for footpath view

    response = requests.get(METADATA_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            return data
        else:
            st.warning(f"No Street View available for location: {lat}, {lon}")
            return None
    else:
        st.error(f"Error fetching metadata: {response.status_code}")
        return None

def calculate_heading(pano_lat, pano_lon, target_lat, target_lon, view_type):
    """
    Calculates the heading from the panorama location to the target location.
    Applies adjustments based on the view type if necessary.
    """
    pano_lat_rad = math.radians(float(pano_lat))
    pano_lon_rad = math.radians(float(pano_lon))
    target_lat_rad = math.radians(float(target_lat))
    target_lon_rad = math.radians(float(target_lon))

    d_lon = target_lon_rad - pano_lon_rad
    x = math.sin(d_lon) * math.cos(target_lat_rad)
    y = math.cos(pano_lat_rad) * math.sin(target_lat_rad) - \
        math.sin(pano_lat_rad) * math.cos(target_lat_rad) * math.cos(d_lon)
    initial_heading = math.atan2(x, y)
    heading = (math.degrees(initial_heading) + 360) % 360

    # Apply adjustment for Footpath View if necessary
    if view_type == 'FV':
        adjustment_angle = 90  # Adjust this value based on testing
        heading = (heading + adjustment_angle) % 360

    return heading

def download_street_view_image(pano_id, heading, location_name, output_dir):
    params = {
        'size': '640x640',
        'pano': pano_id,
        'heading': heading,
        'pitch': '0',
        'key': API_KEY
    }
    response = requests.get(STREET_VIEW_URL, params=params)
    if response.status_code == 200:
        image_path = os.path.join(output_dir, f'{location_name}.jpg')
        with open(image_path, 'wb') as f:
            f.write(response.content)
        return image_path
    else:
        st.error(f"Error fetching image for {location_name}: {response.status_code}")
        return None

def main():
    st.set_page_config(page_title="Street View Image Downloader", layout="wide")

    # Replace use_column_width with use_container_width to avoid deprecation issues
    st.image('Img1.png', use_container_width=True)  # Updated parameter here

    st.title("Loci - Your Ultimate Street View Inspection Site Downloader")

    # Instructions
    st.write("""
    This app allows you to download Google Street View images for a list of locations specified by their latitude and longitude coordinates.

    **Note**: Ensure that the coordinates are precise to the exact location you want to inspect. If the location is on a footpath, the coordinate should be on the footpath, not on the adjacent road.
    """)

    # CSV File Upload with modified label
    uploaded_file = st.file_uploader(
        "Upload CSV file with latitude and longitude coordinates in separate columns - REMINDER: ENSURE THAT THE LATITUDE AND LONGITUDE COORDINATES ARE ACCURATE TO THE LOCATION YOU WANT TO INSPECT. After your location images are presented, click the Download button positioned below the last image.",
        type=['csv']
    )

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            st.error("CSV file must contain 'latitude' and 'longitude' columns.")
            st.stop()
    else:
        st.warning("Please upload a CSV file.")
        st.stop()

    # Output Directory
    output_dir = "downloaded_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process the coordinates
    st.header("Processing Locations...")
    progress_bar = st.progress(0)
    total_locations = len(df)
    images_downloaded = []

    for idx, row in df.iterrows():
        progress = (idx + 1) / total_locations
        progress_bar.progress(progress)

        target_lat = row['latitude']
        target_lon = row['longitude']
        location_name = f'location_{idx + 1}'

        # Use original coordinates directly
        search_lat, search_lon = target_lat, target_lon

        # Use the default view type
        view_type = DEFAULT_VIEW_TYPE

        metadata = get_panorama_metadata(search_lat, search_lon, view_type)
        if metadata:
            pano_id = metadata.get('pano_id')
            pano_location = metadata.get('location', {})
            pano_lat = pano_location.get('lat')
            pano_lon = pano_location.get('lng')
            if pano_lat and pano_lon:
                heading = calculate_heading(pano_lat, pano_lon, target_lat, target_lon, view_type)
                image_path = download_street_view_image(pano_id, heading, location_name, output_dir)
                if image_path:
                    images_downloaded.append((location_name, image_path))
            else:
                st.warning(f"Panorama location not available for {location_name}. Using default heading.")
                image_path = download_street_view_image(pano_id, '0', location_name, output_dir)
                if image_path:
                    images_downloaded.append((location_name, image_path))
        else:
            st.warning(f"Skipping location {location_name} due to missing metadata.")

    progress_bar.empty()

    if images_downloaded:
        st.header("Downloaded Images")

        # Display images
        for name, img_path in images_downloaded:
            st.subheader(name)
            st.image(img_path)  # You can also use use_container_width=True here if desired

        # Create a ZIP file of all images
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for name, img_path in images_downloaded:
                zip_file.write(img_path, arcname=os.path.basename(img_path))

        # Provide the download button
        st.download_button(
            label="Download All Images",
            data=zip_buffer.getvalue(),
            file_name="downloaded_images.zip",
            mime="application/zip"
        )
    else:
        st.info("No images were downloaded.")

if __name__ == '__main__':
    main()
