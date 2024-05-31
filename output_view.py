from urllib.parse import unquote

import altair as alt
import pandas
import requests as req
import streamlit as st

query_params = st.query_params

app_id = query_params.get("app_id")
run_id = query_params.get("run_id")
api_base_url = unquote(query_params.get("url", ""))

error = False

if app_id is None or app_id == "":
    app_id = "temp-demand-forecast"

if run_id is None or run_id == "":
    run_id = "devint-BGS39HySR"

if error:
    st.stop()


@st.experimental_dialog("Enter your API key")
def get_api_key():
    api_key = st.text_input("API Key", type="password")
    if st.button("Submit"):
        st.session_state["api_key"] = api_key
        st.rerun()


# set API key secret from .streamlit/secrets.toml
if st.secrets["NEXTMV_API_KEY"] is not None or st.secrets["NEXTMV_API_KEY"] != "":
    st.session_state["api_key"] = st.secrets["NEXTMV_API_KEY"]
if "api_key" not in st.session_state:
    get_api_key()
    st.stop()

api_key = st.session_state["api_key"]
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

if api_base_url == "":
    api_base_url = "https://api.cloud.nextmv.io"
runs_url = f"{api_base_url}/v1/applications/{app_id}/runs/{run_id}"
response = req.get(runs_url, headers=headers)

if response.status_code != 200:
    st.error(f"Error: {response.text}")
    st.stop()

run_data = response.json()
solutions = run_data["output"]["solutions"]

df = pandas.DataFrame()
for approach in solutions:
    approach_data = pandas.DataFrame(solutions[approach])
    approach_data["approach"] = approach
    df = pandas.concat([df, approach_data])

# Create scatter plot
scatter = (
    alt.Chart(df)
    .mark_circle(size=60)
    .encode(
        x="count",
        y="forecast",
        color="approach",
        tooltip=["count", "forecast", "approach"],
    )
)

# Create trendline
trendline = scatter.transform_regression(
    "count", "forecast", groupby=["approach"]
).mark_line()

# Combine scatter plot and trendline
chart = scatter + trendline

# Make the chart interactive
chart = chart.interactive()

st.altair_chart(chart)
