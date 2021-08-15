import numpy as np
import pandas as pd
import os
from datetime import datetime as dt

dt.now().replace(microsecond=0).isoformat()

R_MAJOR = 6378137.000
DATA_PATH = "data"
sfbay_data = "SFBay.csv"
location_data = "StationLocations.csv"
sfbay_final_data = "sfbay_final.csv"

YEAR_FROM = 1994
YEAR_TO = 2014

ATTRIBUTES = ["TimeStamp","Stations","Distance.from.36","Depth","Fluorescence",
            "Calculated.Chlorophyll","Calculated.Oxygen","Salinity","Temperature",
            "mercator_x","mercator_y"]

def get_time():
    return dt.now().replace(microsecond=0).isoformat()


def to_mercators(lat, lon):
    """
    Define function to switch from lat/long to mercator coordinates
    """
    x = R_MAJOR * np.radians(lon)
    scale = x / lon
    y = (
        180.0
        / np.pi
        * np.log(np.tan(np.pi / 4.0 + lat * (np.pi / 180.0) / 2.0))
        * scale
    )
    return (x, y)


# Read in data
sfbay_data_path = os.path.join(DATA_PATH, sfbay_data)
location_data_path = os.path.join(DATA_PATH, location_data)

print(
    f"[{get_time()}] Starts to process data using [{sfbay_data_path}, {location_data_path}]"
)

sfbay = pd.read_csv(sfbay_data_path, delimiter=";")
locations = pd.read_csv(location_data_path, index_col=False)


#                            #
# Pre-process Locations data #
#                            #

del locations["Comments"]
#
# Stations: Station Number
# lat_deg: North Latitude Degrees
# lat_min: North Latitude Minutes
# lon_deg: West Longitude Degrees
# lon_min: West Longitude Minutes
#
locations_header = ["Stations", "lat_deg", "lat_min", "lon_deg", "lon_min"]
locations.columns = locations_header

# remove minute sign (') and cast to proper types
locations["lat_min"] = locations["lat_min"].str.replace(r"'$", "")
locations["lon_min"] = locations["lon_min"].str.replace(r"'$", "")
locations = locations.astype("float64")
locations["Stations"] = locations["Stations"].astype("int32")

# convert minutes to degrees and sum values
locations["lat"] = locations["lat_deg"] + locations["lat_min"] / 60
locations["lon"] = locations["lon_deg"] - locations["lon_min"] / 60

# drop unnecesary columns
columns_to_drop = [col for col in locations_header if col != "Stations"]
locations = locations.drop(columns_to_drop, axis=1)

# Obtain list of mercator coordinates
mercators = [
    to_mercators(x, y) for x, y in list(zip(locations["lat"], locations["lon"]))
]

# Create mercator column in our df
locations["mercator"] = mercators
# Split that column out into two separate columns - mercator_x and mercator_y
locations[["mercator_x", "mercator_y"]] = locations["mercator"].apply(pd.Series)
locations = locations.drop(columns=["mercator"])


#                        #
# Pre-process SFBay data #
#                        #

sfbay.rename(columns={"Station.Number": "Stations"}, inplace=True)
sfbay["Stations"] = sfbay["Stations"].astype("int32")

# filter on TimeStamp
sfbay = sfbay[
        (pd.to_datetime(sfbay["TimeStamp"]).dt.year >= YEAR_FROM)
        & (pd.to_datetime(sfbay["TimeStamp"]).dt.year <= YEAR_TO)]

# 649, 657
sfbay = sfbay[
        (sfbay["Stations"] != 649)
        & (sfbay["Stations"] != 657)
        & (sfbay["Stations"] != 653)]

# sfbay_final = pd.concat([sfbay, locations], axis=1, join='inner')
sfbay_final = sfbay.merge(
    locations, on="Stations", how="inner"
)  # , suffixes=('_1', '_2'))

# select columns
sfbay_final = sfbay_final[ATTRIBUTES]

sfbay_final_data_path = os.path.join(DATA_PATH, sfbay_final_data)
sfbay_final.to_csv(sfbay_final_data_path, sep=",")

print(f"[{get_time()}] Data has been processed and saved: {sfbay_final_data_path}")
