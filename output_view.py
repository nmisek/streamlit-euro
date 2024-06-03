from urllib.parse import unquote

import altair as alt
import pandas
import requests as req
import streamlit as st

from token_handler import init_auth_state, sendTokenRefreshMessageToParent

st.set_page_config(layout="wide")

query_params = st.query_params

app_id = query_params.get("app_id")
run_id = query_params.get("run_id")
api_base_url = unquote(query_params.get("url", ""))

init_auth_state()

error = False

if app_id is None or app_id == "":
    app_id = "temp-demand-forecast"

if run_id is None or run_id == "":
    run_id = "devint-BGS39HySR"

if api_base_url == "" or api_base_url is None:
    api_base_url = "https://us1.api.staging.nxmv.xyz"

if error:
    st.stop()



# @st.experimental_dialog("Enter your API key")
# def get_api_key():
#     api_key = st.text_input("API Key", type="password")
#     if st.button("Submit"):
#         st.session_state["api_key"] = api_key
#         st.rerun()


# # set API key secret from .streamlit/secrets.toml
# # use either secret if it exists or dialog to get API key
# # check if it's in st.secrets first
# # initialize st.session_state["api_key"] if it's not there
# # if it's there, use it

# # get api key from secrets
# api_key = st.secrets["NEXTMV_API_KEY"]
# if api_key is None or api_key == "":
#     get_api_key()


headers = st.session_state.headers

runs_url = f"{api_base_url}/v1/applications/{app_id}/runs/{run_id}"

response = req.get(runs_url, headers=headers)

if (response.status_code == 403 or response.status_code == 401) and st.session_state.get("api_key") == None:
    sendTokenRefreshMessageToParent()
    st.stop()

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

# widen plot
scatter = scatter.properties(width=800)

# Create trendline
trendline = scatter.transform_regression(
    "count", "forecast", groupby=["approach"]
).mark_line()

# Combine scatter plot and trendline
chart = scatter + trendline

# Make the chart interactive
chart = chart.interactive()
st.altair_chart(chart)

# compute the residuals
df["residual"] = df["count"] - df["forecast"]

# histogram of the residuals colored by approach
bin_size = st.slider(
    "Select bin size for histogram", min_value=1, max_value=100, value=20
)


histogram = (
    alt.Chart(df)
    .mark_bar(opacity=0.75)
    .encode(
        x=alt.X("residual", bin=alt.Bin(step=bin_size), title="Residuals"),
        y="count()",
        color="approach",
    )
)

histogram = histogram.properties(width=800)
st.altair_chart(histogram)
