import pandas as pd

def convert_to_dataframe(odata_response):
    records = odata_response["d"]["results"]

    df = pd.DataFrame(records)
    df = df.drop(columns=["__metadata"])

    return df