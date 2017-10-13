"""
Produce the Giving Tuesday visualizations.
"""
import os.path as op
import sys
import warnings
from collections import defaultdict

import numpy as np
import pandas as pd
import plotly as py
import plotly.graph_objs as go
import us

# Use local classypy until we can fully publish.
sys.path = [op.join(op.dirname(op.abspath(__file__)), '..', 'classypy')] + list(sys.path)  # isort:stay
from classypy import viz
from classypy.devops import find_secrets
from classypy.util.dirs import data_dir, reports_dir


def save_plot(fig, output_path, save_remote=False, sharing="public"):
    """Save a plot either locally, or to a plotly account."""
    if save_remote:
        py.plotly.iplot(fig, filename=op.basename(output_path.replace(".html", "")), sharing=sharing)
    else:
        py.offline.plot(fig, filename=output_path)


def state_name_lookup(abbr):
    """Return a state name, or None"""
    state = us.states.lookup(abbr)
    return state and state.name or None


def plot_map(df, output_path=None, save_remote=False):
    """USA Chloropleth map, via https://plot.ly/python/choropleth-maps/"""
    df["z"] = np.round(100.0 * df["gtv_normalized"] * 52.0 / df["gtv_normalized"].sum(), 1)

    # Add state name
    df["state_name"] = df["state"].map(state_name_lookup)

    colorbar_ticks = [25, 100, 200, 300, 400]  # determined ad-hoc

    data = [dict(
        type="choropleth",
        autocolorscale=False,
        colorscale=viz.classy_colorscale(),
        colorbar=dict(
            title="% above baseline",
            tickmode="array",
            tickvals=colorbar_ticks,
            ticktext=[" {tick}%".format(tick=tick) for tick in colorbar_ticks],
            ticklen=5,
        ),
        locationmode="USA-states",
        locations=df["state"],
        text=df.apply(lambda row: "{name}<br>{pct}%".format(name=row["state_name"], pct=row["z"]), axis=1),
        hoverinfo="text",
        z=df["z"],
    )]

    layout = dict(
        title="Hurricane Harvey<br>Disaster Relief Fundraising<br>August 25 - September 4, 2017",
        font=viz.classy_font(),
        geo=dict(
            scope="usa",
            projection=dict(type="albers usa"),
            showlakes=False,
        ),
        width=700,
        height=500,
    )

    fig = dict(data=data, layout=layout)
    save_plot(fig, output_path=output_path, save_remote=save_remote)


def plot_lines(lines_df, output_path=None, save_remote=False):
    """Line chart showing fundraising trajectory over time."""
    # Label column has category and specific event.

    event_labels = defaultdict(lambda: '')
    event_labels.update({
        'gt 2015': '2015',
        'gt 2016': '2016',
        'eoy 2015': '2015',
        'eoy 2016': '2016',
        'hurricane harvey': 'Hurricane Harvey',
        'louisiana flooding': 'Louisiana Flooding',
    })

    lines_df["category"] = lines_df["label"].map(
        lambda lbl: lbl.split(":")[0])
    lines_df["event"] = lines_df["label"].map(
        lambda lbl: event_labels[lbl.split(":")[1].strip()])
    lines_df["pct_transactions"] *= 100

    event_dfs = (
        lines_df[lines_df["label"].isin(("gt: gt 2015", "gt: gt 2016"))],
        lines_df[lines_df["label"].isin(("eoy: eoy 2015", "eoy: eoy 2016"))],
        lines_df[lines_df["label"].isin(("disaster: hurricane harvey", "disaster: louisiana flooding"))],
    )

    # gt is greatest
    ymax = event_dfs[0]["pct_transactions"].max()

    # Create traces
    event_traces = [[go.Scatter(
        x=trace_df["diff"].values,
        y=trace_df["pct_transactions"].values,
        mode="lines",
        legendgroup=trace_df["event"].unique()[0],
        name=trace_df["event"].unique()[0],
        line=dict(width=4, color=["#f77462", "#50d1bf"][ti]),
    ) for ti, (_, trace_df) in enumerate(event_df.groupby("event"))] for event_df in event_dfs]

    fig = py.tools.make_subplots(rows=1, cols=3, print_grid=False, subplot_titles=(
        "Giving Tuesday", "December 31", "Disaster Relief"))

    for ei in range(3):
        fi, xaxis, yaxis = ei + 1, "xaxis%d" % (ei + 1), "yaxis%d" % (ei + 1)

        # Lay out the axes
        fig["layout"][xaxis].update(
            showgrid=True)
        fig["layout"][yaxis].update(
            range=[0, ymax],
            showgrid=True,
            ticksuffix="%")

        if ei == 1:
            fig["layout"][xaxis].update(
                title="Days after event")
        if ei == 0:
            fig["layout"][yaxis].update(
                title="% of 13 day total")

        for sc in event_traces[ei]:
            # Add the trace
            fig.append_trace(sc, 1, fi)

    fig["layout"].update(
        title="Daily Fundraising During Events",
        font=viz.classy_font(),
        showlegend=False,
        width=900,
        height=440,
    )
    save_plot(fig, output_path=output_path, save_remote=save_remote)


def plot_bars(df, output_path=None, save_remote=False):
    """Show bar plot of various metrics, grouped by event type."""
    # Filter to just the events we want
    df = df[df["supporter_class"].isin(("#GT", "EOY", "Harvey"))]
    df["supporter_class"] = df["supporter_class"].map(lambda lbl: {
        "#GT": "Giving Tuesday 2016",
        "EOY": "December 31, 2016",
        "Harvey": "Hurricane Harvey",
    }[lbl])

    # Massage data to percentages of what we want.
    df["donor_retention"] = 100 * (1.0 - df["pct_ended_on_this_date"])
    df["pct_multi_gave"] *= 100.0
    df["pct_fundraising_afterwards"] *= 100.0

    # Only keep data we want, with names we want.
    df = df.set_index("supporter_class")
    df = df[["donor_retention", "pct_multi_gave", "pct_fundraising_afterwards"]]
    df = df.rename(columns={
        "donor_retention": "New Donor<br>Retention",
        "pct_multi_gave": "Donors Giving<br>Multiple Times<br>During Event",
        "pct_fundraising_afterwards": "Donors Becoming<br>Fundraisers Within<br>90 Days"
    })

    # Transpose, so we can grab by event as key.
    df = df.T

    data = [go.Bar(
        x=df[event_name].keys(),
        y=df[event_name].values,
        name=event_name,
        marker=dict(color=list(viz.classy_colors().values())[ei]),
    ) for ei, event_name in enumerate(df.columns)]

    layout = go.Layout(
        font=viz.classy_font(),
        barmode="group",
        yaxis=dict(
            ticksuffix="%"
        ),
        legend=dict(x=0.55, y=1),
        width=500,
        height=500,
    )

    fig = go.Figure(data=data, layout=layout)
    save_plot(fig, output_path=output_path, save_remote=save_remote)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--save-remote", action="store_true",
                        help="Save figure to a plotly account.")
    parser.add_argument("--plots", nargs="?", default="map,lines,bars")
    args = vars(parser.parse_args())

    # Manipulate args
    plots = args.pop("plots").split(",")

    if args["save_remote"]:
        secrets = find_secrets()
        py.tools.set_credentials_file(
            username=secrets["PLOTLY_USERNAME"], api_key=secrets["PLOTLY_API_KEY"])

    # Construct paths
    paths = {
        "csv_path": {
            "map": "hurricane_harvey-disaster_relief_states.csv",
            "lines": "fundraising-trajectories.csv",
            "bars": "event-comparisons.csv",
        },
        "output_path": {
            "map": "gt-2017-map.html",
            "lines": "gt-2017-lines.html",
            "bars": "gt-2017-bars.html",
        }
    }
    paths["csv_path"] = {key: op.join(data_dir(subdir="processed"), val) for key, val in paths["csv_path"].items()}
    paths["output_path"] = {key: op.join(reports_dir(), val) for key, val in paths["output_path"].items()}

    # Plot plots
    if "map" in plots:
        plot_map(pd.read_csv(paths["csv_path"]["map"]), output_path=paths["output_path"]["map"], **args)

    # Line charts
    if "lines" in plots:
        plot_lines(pd.read_csv(paths["csv_path"]["lines"]), output_path=paths["output_path"]["lines"], **args)

    # Bar charts
    if "bars" in plots:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plot_bars(pd.read_csv(paths["csv_path"]["bars"]), output_path=paths["output_path"]["bars"], **args)
