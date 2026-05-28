from func.get_data import fetch_odata_data
from func.transform_data import convert_to_dataframe
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    raw = fetch_odata_data(os.getenv("url"), os.getenv("username1"), os.getenv("password"))
    df = convert_to_dataframe(raw)
    try:
        print(df.head())
    except Exception:
        print(df)

if __name__ == "__main__":
    main()