import streamlit as st
import json
import csv
from datetime import datetime
import pytz
import requests
import time
import io

@st.cache_data
def load_timezone(file="region_info.json"):
    with open(file, 'r') as f:
        return json.load(f)

# def get_key(username, filename="secret.csv"):
#     with open(filename, mode='r') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             if row['user'] == username:
#                 return row['key']
#     return None

def get_key(username):
    return st.secrets["general"].get(username)


def convert_timezones(start_dt, end_dt, outage=""):
    API_KEY = get_key("katy")
    if not API_KEY:
        st.error("API key not found for user 'katy'")
        return None

    region_info = load_timezone()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Region', 'Planned Outage Start Date/Time', 'Planned Outage End Date/Time'])

    # Vancouver info
    for item in region_info:
        if item["region"] == "Vancouver, Canada":
            Vancouver_region = item["region"]
            Vancouver_tz = item["timezone"]

    start_end_input = [start_dt, end_dt]
    start_end_input_result = [Vancouver_region]
    start_end_timestamp = []

    for dt in start_end_input:
        localized_dt = pytz.timezone(Vancouver_tz).localize(dt)
        input_timestamp = int(localized_dt.timestamp())
        start_end_timestamp.append(input_timestamp)

        url = f"http://api.timezonedb.com/v2.1/get-time-zone?key={API_KEY}&format=json&by=zone&zone={Vancouver_tz}&time={input_timestamp}"
        response = requests.get(url)
        data = response.json()
        abbreviation = data["abbreviation"]

        formatted_input = localized_dt.strftime("%a, %b %d, %Y at %#I:%M %p ") + abbreviation
        start_end_input_result.append(formatted_input)

    writer.writerow([start_end_input_result[0], start_end_input_result[1], start_end_input_result[2]])

    time.sleep(1)

    for item in region_info:
        if item["region"] != "Vancouver, Canada":
            target_region = item["region"]
            target_region_tz = item["timezone"]
            target_result = [target_region]

            for input in start_end_timestamp:
                target_url = f"http://api.timezonedb.com/v2.1/convert-time-zone?key={API_KEY}&format=json&from={Vancouver_tz}&to={target_region_tz}&time={input}"
                target_response = requests.get(target_url)
                time.sleep(2)

                target_data = target_response.json()
                target_timestamp = target_data["toTimestamp"]
                target_abbreviation = target_data["toAbbreviation"]

                target_tz = pytz.timezone(target_region_tz)
                target_time = datetime.fromtimestamp(target_timestamp, target_tz)
                formatted_target = target_time.strftime("%a, %b %d, %Y at %#I:%M %p ") + target_abbreviation
                target_result.append(formatted_target)

            writer.writerow([target_result[0], target_result[1], target_result[2]])

    return output.getvalue()


# Streamlit App
st.title("Outage Timezone Converter")

# Hold form results
csv_result = None

with st.form("timezone_form"):
    st.markdown("### Select Start and End Date/Time")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")

    with col2:
        start_time = st.time_input("Start Time")
        end_time = st.time_input("End Time")

    outage = st.text_input("Outage Description (optional)")

    submitted = st.form_submit_button("Convert")

    if submitted:
        try:
            # Combine date and time
            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(end_date, end_time)

            if end_dt <= start_dt:
                st.error("End date/time must be after start date/time.")
            else:
                csv_result = convert_timezones(start_dt, end_dt, outage)
                if csv_result:
                    st.session_state['csv_result'] = csv_result
                    st.success("Conversion complete! Download available below.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display download button AFTER form
if 'csv_result' in st.session_state:
    st.download_button(
        label="Download CSV",
        data=st.session_state['csv_result'],
        file_name="outage_converted_times.csv",
        mime="text/csv"
    )
