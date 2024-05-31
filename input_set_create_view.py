import json
import random
import string
from datetime import datetime
from urllib.parse import unquote

import pandas
import pytz
import requests
import streamlit as st
from dateutil.parser import parse

query_params = st.query_params

app_id = query_params.get("app_id")
api_base_url = unquote(query_params.get("url", ""))

error = False

if app_id is None or app_id == "":
    app_id = "my-scheds"

if error:
    st.stop()


@st.experimental_dialog("Enter your API key")
def get_api_key():
    api_key = st.text_input("API Key", type="password")
    if st.button("Submit"):
        st.session_state["api_key"] = api_key
        st.rerun()


def serialize_input(data):
    """
    Serialize the instance data in JSON
    """
    return json.dumps(
        data,
        default=lambda x: (
            x.to_json(orient="table") if isinstance(x, pandas.DataFrame) else str(x)
        ),
    )


def create_input(data_scenario, headers, id, name):
    # get an upload url
    upload_url = f"{api_base_url}/v1/applications/{app_id}/runs/uploadurl"
    response = requests.post(upload_url, headers=headers)
    if response.status_code != 200:
        st.error(
            f"Failed to get an upload URL. Status code: {response.status_code}, message: {response.text}"
        )
        st.stop()

    response_json = response.json()
    response = requests.put(
        url=response_json["upload_url"],
        data=serialize_input(data_scenario),
    )

    input_url = f"{api_base_url}/v1/applications/{app_id}/inputs"

    payload = {
        "id": id,
        "upload_id": response_json["upload_id"],
        "name": name,
        "format": {"input": {"type": "json"}},
    }
    response = requests.post(url=input_url, headers=headers, data=json.dumps(payload))

    return response.json()


def create_input_set(scenario_inputs):
    input_responses = []
    for scenario_input in scenario_inputs:
        json_response = create_input(
            scenario_input["input_data"],
            headers,
            scenario_input["input_id"],
            scenario_input["input_id"],
        )
        input_responses.append(json_response)

    input_set_url = f"{api_base_url}/v1/applications/{app_id}/experiments/inputsets"
    input_set_id = f"scheduling-{random_string(5)}"

    input_info = []
    for single_input in input_responses:
        info = {"id": single_input["id"], "name": single_input["name"]}
        input_info.append(info)

    payload = {
        "id": input_set_id,
        "name": input_set_id,
        "inputs": input_info,
        "description": "",
        "maximum_runs": 50,
    }

    response = requests.post(
        url=input_set_url, headers=headers, data=json.dumps(payload)
    )
    if response.status_code == 200:
        st.subheader(
            f"Successfully created the {input_set_id} input set with {len(input_info)} inputs for the app {app_id}!"
        )
    else:
        st.error("Error creating input set!")
        st.stop()


def random_string(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


# set API key secret from .streamlit/secrets.toml
if st.secrets["NEXTMV_API_KEY"] is not None:
    st.session_state["api_key"] = st.secrets["NEXTMV_API_KEY"]
if "api_key" not in st.session_state:
    get_api_key()
    st.stop()

api_key = st.session_state["api_key"]
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

if api_base_url == "":
    api_base_url = "https://api.cloud.nextmv.io"

st.header("Generate input set for shift scheduling model:")

st.subheader("Input worker availabilities:")
with open("sample-scheduling-input.json") as f:
    sample = json.load(f)
    workers = pandas.DataFrame(sample["workers"])

date = st.date_input("Date of the Schedule:")

# edit all availabilities to the same date
for i in range(len(workers)):
    for j in range(len(workers["availability"][i])):
        start_time = parse(workers["availability"][i][j]["start"]).time()
        end_time = parse(workers["availability"][i][j]["end"]).time()

        start_datetime = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)

        workers["availability"][i][j]["start"] = start_datetime.isoformat()
        workers["availability"][i][j]["end"] = end_datetime.isoformat()

# Create a form for the user to input worker availability
# TODO: make it possible to add more than 2 availabilities per worker
with st.form(key="worker_availability_form"):
    worker_id = st.selectbox("Worker ID", workers["id"].tolist())
    availability_start = st.time_input("Availability Start")
    availability_end = st.time_input("Availability End")
    timezone_offset = st.number_input(
        "Timezone Offset", min_value=-12, max_value=14, value=-5
    )
    append_availability = st.checkbox("Append to existing availabilities", value=True)

    submit_button = st.form_submit_button(label="Update Availability")

    # If the form is submitted, update the availability of the selected worker
    if submit_button:
        start_datetime = datetime.combine(date, availability_start)
        end_datetime = datetime.combine(date, availability_end)

        # Apply timezone offset
        timezone = pytz.FixedOffset(
            timezone_offset * 60
        )  # timezone offset is in minutes
        start_datetime = start_datetime.replace(tzinfo=timezone)
        end_datetime = end_datetime.replace(tzinfo=timezone)

        new_availability = {
            "start": start_datetime.isoformat(),
            "end": end_datetime.isoformat(),
        }

        if append_availability:
            # Append new availability to existing ones
            workers.loc[workers["id"] == worker_id, "availability"].apply(
                lambda x: x.append(new_availability)
            )
        else:
            # Overwrite existing availabilities with the new one
            workers.loc[workers["id"] == worker_id, "availability"] = [new_availability]

    with st.container():
        st.table(workers)

# select app to use for first stage demand forecasting
st.subheader("Select app to use for demand forecasts: ")

# dropdown list of apps from the Nextmv API
apps_url = f"{api_base_url}/v1/applications"
response = requests.get(apps_url, headers=headers)
apps = response.json()
demand_forecast_app_id = st.selectbox("Select app", [app["id"] for app in apps])

# dropdown list of past runs of the demand forecasting app
runs_url = f"{api_base_url}/v1/applications/{demand_forecast_app_id}/runs"
response = requests.get(runs_url, headers=headers)
runs = response.json()["runs"]

# convert to pandas dataframe for better display
df = pandas.DataFrame()

runs = response.json()["runs"]
df = pandas.DataFrame()
columns = ["id", "created_at", "status_v2"]

for run in runs:
    # Select only the desired columns
    selected_run = {column: run[column] for column in columns}
    run_df = pandas.DataFrame([selected_run])
    df = pandas.concat([df, run_df])

col2, col1 = st.columns(2)
df_html = df.to_html(index=False)
for _ in range(13):
    col1.text("")
col1.write(df_html, unsafe_allow_html=True)

# Add a checkbox for each run in the second column
for _ in range(4):
    col2.text("")
selected_runs = []
col2.subheader(
    "Select a past run from demand forecasting to use to generate required workers: "
)
if "id" in df.columns:
    selected_run = col2.radio(" ", df["id"].tolist())
    # Add space between checkboxes
    for _ in range(2):
        col2.text("")
else:
    st.write("Column 'id' not found in DataFrame.")

# Filter DataFrame based on selected runs
if selected_runs:
    selected_df = df[df["id"].isin(selected_runs)]

# Get the selected run results
for _ in range(5):
    col2.text("")

if col2.button("Select run and create input set"):
    result_url = (
        f"{api_base_url}/v1/applications/{demand_forecast_app_id}/runs/{selected_run}"
    )
    response = requests.get(result_url, headers=headers)
    result = response.json()
    solutions = result["output"]["solutions"]
    forecasts = pandas.DataFrame()
    inputs = []
    for approach in solutions:
        approach_data = pandas.DataFrame(solutions[approach])
        approach_data["approach"] = approach
        approach_data = approach_data.rename(columns={"start_time": "start"})
        approach_data = approach_data.rename(columns={"end_time": "end"})

        # select only the forecasts for the date selected
        approach_data = approach_data[
            approach_data["date"] == date.strftime("%Y-%m-%d")
        ]
        forecasts = pandas.concat([forecasts, approach_data])
        selected_columns = ["start", "end", "count"]

        # Create an input for the approach
        input = {
            "workers": workers.to_dict("records"),
            "required_workers": approach_data[selected_columns].to_dict("records"),
        }
        inputs.append({"input_id": f"input-{random_string(5)}", "input_data": input})
    st.subheader("Forecast results for the selected run: ")
    st.write(forecasts)
    create_input_set(inputs)
