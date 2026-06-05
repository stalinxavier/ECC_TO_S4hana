import io
import os
from contextlib import redirect_stdout

import pandas as pd
from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

# Shared in-memory state across tools for the current agent session
_state: dict = {
    "raw_data": None,   # raw JSON from ECC OData
    "ecc_df": None,     # cleaned ECC DataFrame
    "mapping": None,    # LLM field mapping dict
    "s4_df": None,      # S/4HANA-ready DataFrame
}


@tool
def fetch_ecc_data() -> str:
    """Fetch vendor master data from SAP ECC via OData API. Always run this first."""
    from func.get_data import fetch_odata_data

    raw = fetch_odata_data(
        os.getenv("url"),
        os.getenv("username1"),
        os.getenv("password"),
    )
    _state["raw_data"] = raw
    count = len(raw.get("d", {}).get("results", []))
    return f"Fetched {count} vendor records from ECC OData."


@tool
def transform_ecc_data() -> str:
    """Clean and normalize raw ECC data into a structured DataFrame. Run after fetch_ecc_data."""
    from func.transform_data import convert_to_dataframe

    if _state["raw_data"] is None:
        return "No raw data found. Please run fetch_ecc_data first."

    ecc_df = convert_to_dataframe(_state["raw_data"])
    _state["ecc_df"] = ecc_df
    ecc_df.to_csv("output_ecc.csv", index=False)
    return (
        f"Transformed {len(ecc_df)} records with {len(ecc_df.columns)} columns. "
        f"Sample columns: {list(ecc_df.columns[:6])}. Saved to output_ecc.csv."
    )


@tool
def map_fields_with_llm() -> str:
    """Use the LLM to map ECC fields to S/4HANA Business Partner fields and apply the mapping.
    Run after transform_ecc_data. This is the most time-consuming step."""
    from func.map_data import apply_mapping, get_field_mapping

    if _state["ecc_df"] is None:
        return "No ECC DataFrame found. Please run transform_ecc_data first."

    mapping = get_field_mapping(_state["ecc_df"])
    _state["mapping"] = mapping

    s4_df = apply_mapping(_state["ecc_df"], mapping)
    _state["s4_df"] = s4_df
    s4_df.to_csv("output_s4.csv", index=False)

    mapped_fields = [
        info["s4_field"]
        for info in mapping.get("field_mappings", {}).values()
        if info and info.get("s4_field")
    ]
    consolidations = list(mapping.get("consolidations", {}).keys())
    return (
        f"Mapped {len(s4_df)} records to {len(s4_df.columns)} S/4HANA fields. "
        f"Individual mappings: {len(mapped_fields)}. "
        f"Consolidations: {consolidations}. "
        f"Saved to output_s4.csv."
    )


@tool
def preview_data(stage: str = "s4") -> str:
    """Preview the first 5 rows of data at a given pipeline stage.
    stage must be 'ecc' (raw ECC data) or 's4' (mapped S/4HANA data)."""
    df: pd.DataFrame | None = _state["ecc_df"] if stage == "ecc" else _state["s4_df"]
    if df is None:
        return f"No {stage.upper()} data available yet. Run the appropriate pipeline step first."
    return df.head(5).to_string()


@tool
def write_to_s4hana() -> str:
    """Push the mapped S/4HANA data to the target system via OData API.
    Run after map_fields_with_llm. This step creates Business Partner records in S/4HANA."""
    from func.write_data import write_to_s4hana as _write

    if _state["s4_df"] is None:
        return "No S/4HANA DataFrame found. Please run map_fields_with_llm first."

    buf = io.StringIO()
    with redirect_stdout(buf):
        _write(_state["s4_df"])
    return buf.getvalue().strip()


@tool
def get_pipeline_status() -> str:
    """Return the current status of the migration pipeline — which stages have completed
    and how many records are loaded at each stage."""
    lines = []
    lines.append(f"[1] fetch_ecc_data    : {'Done — ' + str(len(_state['raw_data'].get('d', {}).get('results', []))) + ' records' if _state['raw_data'] else 'Not run'}")
    lines.append(f"[2] transform_ecc_data: {'Done — ' + str(len(_state['ecc_df'])) + ' rows, ' + str(len(_state['ecc_df'].columns)) + ' columns' if _state['ecc_df'] is not None else 'Not run'}")
    lines.append(f"[3] map_fields_with_llm: {'Done — ' + str(len(_state['s4_df'])) + ' rows, ' + str(len(_state['s4_df'].columns)) + ' S/4HANA columns' if _state['s4_df'] is not None else 'Not run'}")
    lines.append(f"[4] write_to_s4hana   : {'Ready to run' if _state['s4_df'] is not None else 'Waiting for step 3'}")
    return "\n".join(lines)
