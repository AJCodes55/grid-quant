from ercot_client import fetch_all_pages , save_data, raw_data_path
import calendar
import os
import time

url = "https://api.ercot.com/api/public-reports/np6-905-cd/spp_node_zone_hub"

def run_pipeline():
    for year in range(2024, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 3:
                break
            last_day = calendar.monthrange(year, month)[1]
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"

            filename = f"ercot_prices_{year}_{month:02d}.parquet"
            filepath = os.path.join(raw_data_path, filename)
            if os.path.exists(filepath):
                print(f"Skipping {start_date} to {end_date} because it already exists")
                continue
            print(f"Would fetch: {start_date} to {end_date}")
            df = fetch_all_pages(url, extra_params={
           "deliveryDateFrom": start_date,
           "deliveryDateTo": end_date,
           "settlementPoint": "HB_NORTH"})
            if df.empty:
                print(f"Warning: empty data for {start_date}, skipping save")
                continue
            save_data(df, start_date, "ercot_prices")
            print(f"Saved: {filename}")
            time.sleep(3)

if __name__ == "__main__":
    run_pipeline()