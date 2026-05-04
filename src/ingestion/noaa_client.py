import requests
import os
import pandas as pd
import time
import calendar

from dotenv import load_dotenv
load_dotenv()
# This gives you the directory where data_fetcher.py lives
script_dir = os.path.dirname(os.path.abspath(__file__))

# Go up two levels to GridQuant/, then into data/raw/
project_root = os.path.dirname(os.path.dirname(script_dir))
raw_data_path = os.path.join(project_root, "data", "raw")

url = "https://www.ncei.noaa.gov/cdo-web/api/v2/data"
    
    
def parse_response(response_json):

    records = response_json.get('results', [])
    df = pd.DataFrame(records)

    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])

    wide_df = df.pivot_table(
        index="date",
        columns="datatype",
        values="value",
        aggfunc="mean"   
    )
    wide_df = wide_df.reset_index()
    wide_df.columns.name = None
    wide_df['TMAX'] = wide_df['TMAX']/10 
    wide_df['TMIN'] = wide_df['TMIN']/10 
    wide_df['AWND'] = wide_df['AWND']/10

    return wide_df
    


def fetch_all_pages(url, extra_params={}):
    headers = {
        "token": os.getenv("NOAA_TOKEN"),
    }
    all_data = []
    offsets = 1
    limit = 1000
    while True:
        params = {
            "limit": limit,
            "offset": offsets
        }
        params.update(extra_params)
        offsets += limit
        response = requests.get(url, headers=headers, params=params)  #api call
        if response.status_code == 200:   # parse response
            data = response.json()   
            df = parse_response(data)
            all_data.append(df)

            results = data.get('results', [])
            if len (results) < limit:
                break
        elif response.status_code in [429, 503]:
            print(f"Server unavailable ({response.status_code}). Waiting 60 seconds...")
            time.sleep(60)
            offsets -= limit  # retry same page
        else:
                raise Exception(f"Unhandled error: {response.status_code}")
    return pd.concat(all_data)



def save_data(df, start_date, dataset_name):
    os.makedirs(raw_data_path, exist_ok=True)
    filename = f"{dataset_name}_{start_date[:7].replace('-', '_')}.parquet"
    filepath = os.path.join(raw_data_path, filename)
    df.to_parquet(filepath)



def run_pipeline():
    for year in range(2018, 2025):
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"

            filename = f"noaa_weather_{year}_{month:02d}.parquet"
            filepath = os.path.join(raw_data_path, filename)
            if os.path.exists(filepath):
                print(f"Skipping {start_date} to {end_date} because it already exists")
                continue
            print(f"Would fetch: {start_date} to {end_date}")
            df = fetch_all_pages(url, extra_params={
                "datasetid": "GHCND",
                "stationid": "GHCND:USW00003927",
                "datatypeid": "TMAX,TMIN,AWND,PRCP,RHAV",
                "startdate": start_date,
                "enddate": end_date
                })
            save_data(df, start_date, "noaa_weather")
            print(f"Saved: {filename}")
            time.sleep(3)


if __name__ == "__main__":
    run_pipeline()