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

api_key = os.getenv("ERCOT_API_KEY")




def get_auth_token():
    url = "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
    data = {
        "username": os.getenv("ERCOT_USERNAME"),
        "password": os.getenv("ERCOT_PASSWORD"),
        "client_id": os.getenv("ERCOT_CLIENT_ID"),
        "scope": "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access",
        "grant_type": "password",
        "response_type": "id_token",
    }
    

    response = requests.post(url, data=data)
    print(response.status_code)
    print(response.json().keys())
    token = response.json()['id_token']
    return token

token = None
token_fetched_at = None

#token refresh logic
def get_valid_token():
    global token, token_fetched_at
    # if no token exists OR token is older than 55 minutes
    if token is None or token_fetched_at is None or time.time() - token_fetched_at > 55 * 60:
        token = get_auth_token()
        token_fetched_at = time.time()
    
    return token
def parse_response(response_json):

    columns = [field['name'] for field in response_json['fields']]
    data = response_json['data']
    df = pd.DataFrame(data, columns=columns)
    
    return df


#pagination logic
def fetch_all_pages(url,extra_params={}):
    headers = {
    "Ocp-Apim-Subscription-Key": os.getenv("ERCOT_API_KEY"),
    "Authorization": f"Bearer {get_valid_token()}"
}
    all_data = []
    current_page = 1

    while True:
        params = {
            "size": 2000000,
            "page": current_page
        }
        params.update(extra_params)
        current_page += 1
        response = requests.get(url, headers=headers, params=params)  #api call
        if response.status_code == 200:   # parse response
            data = response.json()   
            df = parse_response(data)
            all_data.append(df)
            total_pages = data['_meta']['totalPages']

            if current_page > total_pages:
                break
        elif response.status_code == 429:
            print("Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            current_page -= 1  # retry same page
        elif response.status_code == 401:
            print("Token expired. Refreshing...")
            headers["Authorization"] = f"Bearer {get_valid_token()}"
            current_page -= 1  # retry same page
        else:
                raise Exception(f"Unhandled error: {response.status_code}")
    return pd.concat(all_data)



def save_data(df, start_date, dataset_name):
    os.makedirs(raw_data_path, exist_ok=True)
    filename = f"{dataset_name}_{start_date[:7].replace('-', '_')}.parquet"
    filepath = os.path.join(raw_data_path, filename)
    df.to_parquet(filepath)





#if __name__ == "__main__":
    ##run_pipeline()


