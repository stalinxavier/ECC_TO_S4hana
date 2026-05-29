import pandas as pd

def convert_to_dataframe(odata_response, csv_file_path="output1.csv"):
    records = odata_response["d"]["results"]

    df = pd.DataFrame(records)
    df = df.drop(columns=["__metadata"])

    # 1. Convert SAP date format /Date(ms)/ to datetime
    df["Erdat"] = pd.to_datetime(
        df["Erdat"].str.extract(r'/Date\((\d+)\)/')[0].astype(float), unit="ms"
    )

    # 2. Trim whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())

    # 3. Normalize city casing
    df["Ort01"] = df["Ort01"].str.title()

    # 4. Convert "True"/"False" strings to booleans
    bool_cols = [col for col in df.columns if df[col].isin(["True", "False"]).all()]
    df[bool_cols] = df[bool_cols].apply(lambda col: col.map({"True": True, "False": False}))

    # 5. Zero-pad vendor number to 10 digits (SAP standard)
    df["Lifnr"] = df["Lifnr"].astype(str).str.zfill(10)

    # 6. Normalize zero-padded numeric fields to plain "0"
    for col in ["Bbbnr", "Bbsnr"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lstrip("0").replace("", "0")

    df.to_csv(csv_file_path, index=False)

    return df