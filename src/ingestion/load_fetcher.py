from ercot_client import fetch_all_pages , save_data, raw_data_path
import calendar
import os
import time

url = "https://api.ercot.com/api/public-reports/np6-345-cd/act_sys_load_by_wzn"

def run_pipeline():
    for year in range(2018, 2025):
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"

            filename = f"ercot_load_{year}_{month:02d}.parquet"
            filepath = os.path.join(raw_data_path, filename)
            if os.path.exists(filepath):
                print(f"Skipping {start_date} to {end_date} because it already exists")
                continue
            print(f"Would fetch: {start_date} to {end_date}")
            df = fetch_all_pages(url, extra_params={
            "operatingDayFrom": start_date,
            "operatingDayTo": end_date})
            save_data(df, start_date, "ercot_load")
            print(f"Saved: {filename}")
            time.sleep(3)

if __name__ == "__main__":
    run_pipeline()