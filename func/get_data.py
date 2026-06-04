import requests
from hdbcli import dbapi
from dotenv import load_dotenv
import os
load_dotenv()

url=os.getenv("url")
username=os.getenv("username1")
password=os.getenv("password")


def fetch_odata_data(url, username, password):
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(
        url,
        headers=headers,
        auth=(username, password)
    )

    response.raise_for_status()

    return response.json()


data = fetch_odata_data(
    url,
    username,
    password
)

# print(data)