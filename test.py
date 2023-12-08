import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import requests
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from shapely.geometry import LineString
from pyproj import Transformer

st.title('Kult superapp')

def transformer(coords):
    '''Transformerer koordinater fra WGS84 til UTM 33N'''

    transformer = Transformer.from_crs(4326, 25833)
    return [transformer.transform(lon, lat) for lat, lon in coords]

def interpolate_points_shapely(coords, distance_m=1):
    '''Interpolerer punkter langs ei linje med en gitt avstand
    
    Returnerer en liste med koordinater
    '''

    utm_coords = transformer(coords)
    line = LineString(utm_coords)
    st.write(f'Linjelengde: {round(line.length)}')
    num_points = int(line.length / distance_m)
    points = []
    for i in range(num_points + 1):
        point = line.interpolate(distance_m * i)
        points.append([point.x, point.y])
    return points

def chunk_list(lst, chunk_size):
    """Deler opp i deler på maks 50 punkter, som er maks for geonorge sin API"""

    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

@st.cache_data
def hent_hogder(koordiater, opplosning=1):
        '''Henter ut høyde for en liste med koordinater'''

        points = interpolate_points_shapely(koordiater)
        df = pd.DataFrame()
        chunk_size = 50
        for chunk in chunk_list(points, chunk_size):
            r = requests.get(f'https://ws.geonorge.no/hoydedata/v1/punkt?koordsys=25833&punkter={chunk}&geojson=false')
            data = r.json()

            temp_df = pd.DataFrame(data['punkter'])
            df = pd.concat([df, temp_df], ignore_index=True)
        return df


m = folium.Map(location=[62.14497, 9.404296], zoom_start=5)
#Legger til norgeskart som bakgrunn
folium.raster_layers.WmsTileLayer(
    url="https://opencache.statkart.no/gatekeeper/gk/gk.open_gmaps?layers=topo4&zoom={z}&x={x}&y={y}",
    name="Norgeskart",
    fmt="image/png",
    layers="topo4",
    attr='<a href="http://www.kartverket.no/">Kartverket</a>',
    transparent=True,
    overlay=True,
    control=True,
).add_to(m)
#Legger til tegneverktøy
draw = Draw(
draw_options={
    'polyline': {'shapeOptions': {
            'color': '#0000FF',  # Change this to your desired color
        }
    },
    'polygon': False,
    'rectangle': False,
    'circle': False,
    'circlemarker': False,
    'marker': False
}, position='topleft', filename='skredkart.geojson', export=True,
)
draw.add_to(m)

output = st_folium(m, width=900, height=700)
#st.write(output)

try:
    koordiater = output["all_drawings"][0]["geometry"]["coordinates"]
    df = hent_hogder(koordiater)

    df['M'] = df.index
    df.columns = [col.upper() for col in df.columns]
    df_ok = True
except TypeError:
    st.error('Du må tegne ei profillinje')
    df_ok = False

if df_ok:
    st.dataframe(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df.Z, mode='lines', name='Terreng'))
    #fig.add_trace(go.Scatter(x=[terrengvinkel], y=[bruddhøgde(snøhøgde, terrengvinkel)], mode='markers', name='Valgte parametere', marker=dict(color='red')))
    #fig.update_layout(title='Flaktykkelse vs Terrengvinkel', xaxis_title='Terrengvinkel (grader)', yaxis_title='Flaktykkelse (cm)')

    st.plotly_chart(fig)
