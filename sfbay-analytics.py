#!/usr/bin/env python3

# imports
from bokeh.plotting import figure, ColumnDataSource
from bokeh.tile_providers import get_provider, Vendors
from bokeh.palettes import RdYlBu, PuOr, PiYG
from bokeh.transform import linear_cmap, factor_cmap
from bokeh.layouts import row, column
from bokeh.models import (
    GeoJSONDataSource,
    LinearColorMapper,
    ColorBar,
    NumeralTickFormatter,
    PreText,
    Select
)

from bokeh.models.widgets import Div
from bokeh.layouts import gridplot
from bokeh.io import curdoc
from bokeh.models import CustomJS, Slider, RangeSlider

import pandas as pd
import os

# constants
DATA_PATH = "data/"
FILE_NAME = "sfbay_final.csv"
INITIAL_YEAR = 2000
INITIAL_MONTH = 5
INITIAL_STATION = 5


def get_data():
    data_path = os.path.join(DATA_PATH, FILE_NAME)
    return pd.read_csv(data_path, delimiter=",")


def get_initial_top_data(df):
    df_selected = df[
        (pd.to_datetime(df["TimeStamp"]).dt.year == INITIAL_YEAR)
        & (pd.to_datetime(df["TimeStamp"]).dt.month == INITIAL_MONTH)
    ]

    df_grouped = df_selected.groupby(["Stations"]).mean()

    return ColumnDataSource(data=df_grouped)


def get_initial_bottom_data(df):
    df_selected = df[
        (sfbay["Stations"] == INITIAL_STATION)
    ]

    return ColumnDataSource(data=df_selected)


def update_top_data(attr, old, new):

    # Get the current slider values
    year = year_slider.value
    month = month_slider.value

    sfbay_selected = sfbay[
        (pd.to_datetime(sfbay["TimeStamp"]).dt.year == year)
        & (pd.to_datetime(sfbay["TimeStamp"]).dt.month == month)
    ]

    sfbay_grouped = sfbay_selected.groupby(["Stations"]).mean()

    source_top.data = sfbay_grouped


def update_bottom_data(attr, old, new):

    # Get the current slider values
    station_no = station_slider.value

    sfbay_selected = sfbay[
        (sfbay["Stations"] == station_no)
    ]

    source_bottom.data = sfbay_selected


def create_figure(title, tooltips):
    return figure(
        title=title,
        x_axis_type="mercator",
        y_axis_type="mercator",
        x_axis_label="Longitude",
        y_axis_label="Latitude",
        tooltips=tooltips,
    )


def create_cmap(source_top, palette, field):
    return linear_cmap(
        field_name=field,
        palette=palette,
        low=source_top.data[field].min(),
        high=source_top.data[field].max(),
    )


def create_colorbar(color_mapper):
    return ColorBar(
        color_mapper=color_mapper["transform"],
        formatter=NumeralTickFormatter(format="0.0[0000]"),
        label_standoff=13,
        width=8,
        location=(0, 0),
    )


def create_figure_wrapper(source_top, field_name, palette, tile, circle_size=15):

    MONO_COLOR = False

    if isinstance(palette, str):
        MONO_COLOR = True

    if MONO_COLOR:
        color_mapper = palette
    else:
        color_mapper = create_cmap(source_top, palette, field_name)

    # Create figure
    tooltips = [("Station Number", "@Stations")]
    if field_name != "Stations":
        tooltips.append((field_name, f"@{field_name}"))

    title = f"{field_name} @ San Francisco Bay Area"
    fig = create_figure(title, tooltips)

    # Add map tile
    fig.add_tile(tile)

    # Add points using mercator coordinates
    fig.circle(
        x="mercator_x",
        y="mercator_y",
        color=color_mapper,
        source=source_top,
        size=circle_size,
        line_color="#000000",
        line_width=1.5,
        fill_alpha=0.7,
    )

    if not MONO_COLOR:
        # Defines color bar
        color_bar = create_colorbar(color_mapper)
        # Set color_bar location
        fig.add_layout(color_bar, "right")

    return fig


def create_top_figures():
    default_tile = get_provider(Vendors.CARTODBPOSITRON_RETINA)

    # temperature_field_name = "Temperature"
    # temperature_palette = RdYlBu[11]
    # temperature = create_figure_wrapper(
    #     source_top, temperature_field_name, temperature_palette, default_tile
    # )

    chlorophyll_field_name = "Chlorophyll"
    chlorophyll_palette = PiYG[11]
    chlorophyll = create_figure_wrapper(
        source_top, chlorophyll_field_name, chlorophyll_palette, default_tile
    )

    salinity_field_name = "Salinity"
    salinity_palette = PuOr[11]
    salinity = create_figure_wrapper(
        source_top, salinity_field_name, salinity_palette, default_tile
    )

    fluorescence_field_name = "Fluorescence"
    fluorescence_palette = PiYG[11]
    fluorescence = create_figure_wrapper(
        source_top, fluorescence_field_name, fluorescence_palette, default_tile
    )

    station_tile = get_provider(Vendors.OSM)
    station_field_name = "Stations"
    station_palette = "blue"
    stations = create_figure_wrapper(
        source_top, station_field_name, station_palette, station_tile, circle_size=10
    )

    return chlorophyll, salinity, fluorescence, stations


def create_timeline(col, xl, yl):
    tools_timeline = 'pan,wheel_zoom,xbox_select,reset'

    fig = figure(title=col,
                 x_axis_label=xl,
                 y_axis_label=yl,
                 plot_width=900,
                 plot_height=200,
                 tools=tools_timeline,
                 active_drag="xbox_select")
    fig.line('Id', col, source=source_bottom)
    fig.circle('Id', col, size=1, source=source_bottom, color=None,
               selection_color="orange")

    return fig


def create_correlation(xl, yl):
    tools_corr = 'pan,wheel_zoom,box_select,reset'

    fig = figure(title=f"{xl} vs. {yl}",
                  x_axis_label=xl,
                  y_axis_label=yl,
                  plot_width=350,
                  plot_height=350,
                  tools=tools_corr)

    fig.circle(xl, yl, size=2, source=source_bottom,
                selection_color="orange", alpha=0.6, nonselection_alpha=0.1,
                selection_alpha=0.4)

    return fig


def create_bottom_figures():

    t_o_corr = create_correlation("Temperature", "Oxygen")
    temperature = create_timeline("Temperature", "Time", "Celsius degree")
    oxygen = create_timeline("Oxygen", "Time", "Celsius Mg/Liter")

    return t_o_corr, temperature, oxygen


def create_top_widgets(sfbay):
    timestamp_col = pd.to_datetime(sfbay["TimeStamp"])

    sfbay_year = timestamp_col.dt.year
    max_year = max(sfbay_year)
    min_year = min(sfbay_year)

    sfbay_month = timestamp_col.dt.month
    max_month = max(sfbay_month)
    min_month = min(sfbay_month)

    year_slider = Slider(
        title="Year of the Measurement",
        start=min_year,
        end=max_year,
        step=1,
        value=INITIAL_YEAR,
    )
    month_slider = Slider(
        title="Month of the Measurement",
        start=min_month,
        end=max_month,
        step=1,
        value=INITIAL_MONTH,
    )

    return year_slider, month_slider


def create_bottom_widgets(sfbay):
    station_col = sfbay["Stations"]

    max_station = max(station_col)
    min_station = min(station_col)

    station_slider = Slider(
        title="Station Number (ID)",
        start=min_station,
        end=max_station,
        step=1,
        value=INITIAL_STATION,
    )

    return station_slider


def construct_html(top_elements, bottom_elements):

    page_title = Div(
        text="""Water Quality at
    the SF Bay-Area""",
        width=350,
        height=100,
        style={
            "font-size": "25pt",
            "color": "#0086b3",
            "font-weight": "bold",
            "text-align": "left",
            "font-family": "Arial, Helvetica, sans-serif",
        },
    )

    description = Div(
        text="""The graphics below depict important measurements of water quality in
    the San Francisco Bay Area from 1994 to 2004.
    Interact with the graphs by navigating, zooming, or setting the time period for the data collection. """,
        width=500,
        height=100,
    )

    intro = column(page_title, description)
    space_1 = Div(text="""""", width=50, height=100)
    space_2 = Div(text="""""", width=40, height=15)
    space_3 = Div(text="""""", width=10, height=10)

    left_top = column(row(space_1, intro), top_elements["stations"])

    right_top = gridplot(
        [
            [top_elements["salinity"], top_elements["controls"]],
            [top_elements["chlorophyll"], top_elements["fluorescence"]],
        ],
        plot_width=450,
        plot_height=400,
    )

    left_bottom = column(row(space_2, bottom_elements["controls"]), row(space_3, bottom_elements["t_o_corr"]))

    right_bottom = gridplot(
        [
            [bottom_elements["temperature"], bottom_elements["oxygen"]]
        ],
        plot_width=600,
        plot_height=350,
    )

    top_grid = row(left_top, right_top)
    bottom_grid = row(left_bottom, right_bottom)

    layout = column(top_grid, bottom_grid)

    return layout

### GET DATA ###
sfbay = get_data()
source_top = get_initial_top_data(sfbay)
source_bottom = get_initial_bottom_data(sfbay)

### CREATE FIGURES ###
chlorophyll, salinity, fluorescence, stations = create_top_figures()
t_o_corr, temperature, oxygen = create_bottom_figures()

### CREATE WIDGETS ###
## TOP
year_slider, month_slider = create_top_widgets(
    sfbay
)
top_widgets = [year_slider, month_slider]
top_controls = column(top_widgets)
for widget in top_widgets:
    widget.on_change("value", update_top_data)

## BOTTOM
station_slider = create_bottom_widgets(
    sfbay
)
station_slider.on_change("value", update_bottom_data)
bottom_controls = column(station_slider)

### CONSTRUCT HTML ###
layout = construct_html(
    {
        "stations": stations,
        "salinity": salinity,
        "chlorophyll": chlorophyll,
        "fluorescence": fluorescence,
        "controls": top_controls,
    },
    {
        "t_o_corr": t_o_corr,
        "temperature": temperature,
        "oxygen": oxygen,
        "controls": bottom_controls,
    }
)

curdoc().add_root(layout)
curdoc().title = "Bay Area Water Quality"