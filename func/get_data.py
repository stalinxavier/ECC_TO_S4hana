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

    try:
        response = requests.get(
            url,
            headers=headers,
            auth=(username, password),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectTimeout:
        raise ConnectionError(f"Cannot reach SAP ECC server at {url}. Check that the server is running and you are on the correct network/VPN.")
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Connection refused by SAP ECC server at {url}. Verify the host, port, and network access.")


if __name__ == "__main__":
    data = fetch_odata_data(url, username, password)
    print(data)