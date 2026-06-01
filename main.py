from func.get_data import fetch_odata_data
from func.transform_data import convert_to_dataframe
from func.map_data import get_field_mapping, apply_mapping
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    # Extract
    raw = fetch_odata_data(os.getenv("url"), os.getenv("username1"), os.getenv("password"))

    # Transform + clean (writes output1.csv)
    ecc_df = convert_to_dataframe(raw)
    print(f"ECC records loaded: {len(ecc_df)}")

    # LLM field mapping: ECC → S/4HANA
    print("Requesting field mapping from LLM...")
    mapping = get_field_mapping(ecc_df)

    # Apply mapping to produce S/4HANA-ready DataFrame
    s4_df = apply_mapping(ecc_df, mapping)
    s4_df.to_csv("output_s4.csv", index=False)
    print(f"S/4HANA mapped records: {len(s4_df)}")
    print(s4_df.head())

if __name__ == "__main__":
    main()