# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SAP ECC to S/4HANA data migration tool. Fetches vendor/supplier master data (LFA1 table) from an SAP ECC system via OData API, transforms it, uses an LLM (via SAP AI Core) to generate ECC→S/4HANA field mappings, and loads the result to S/4HANA via `hdbcli`.

## Running the Code

No build system — run Python files directly using the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
python main.py
```

Individual stages can also be run standalone (each module loads `.env` and calls itself at module level during development):

```powershell
python func/get_data.py        # prints raw OData JSON
python func/transform_data.py  # writes output1.csv
```

## Architecture

Four-stage ETL pipeline. Entry point is `main.py`; modules live in `func/` and `llm/`.

### `func/` — ETL stages

| Module | Role | Status |
|---|---|---|
| `get_data.py` | Extract — HTTP GET to SAP ECC OData endpoint with Basic Auth | Working |
| `transform_data.py` | Transform — JSON → pandas DataFrame; cleans dates, strings, booleans, zero-padding | Working |
| `map_data.py` | Map — sends ECC column names + sample values to LLM; receives JSON mapping; applies it to produce S/4HANA-ready DataFrame | Working |
| `write_data.py` | Load — upsert S/4HANA-mapped DataFrame into HANA DB via `hdbcli` | Working |

### `llm/` — LLM integration

- `factory_llm.py` — instantiates `ChatOpenAI` via `gen-ai-hub` SAP AI Core proxy; reads all `AICORE_*` env vars
- `model.py` — single shared `map_data_llm` instance (temperature=0) imported by `map_data.py`

### Data flow

```
SAP ECC OData
  → fetch_odata_data()           → raw JSON
  → convert_to_dataframe()       → ecc_df  (writes output1.csv)
  → get_field_mapping(ecc_df)    → mapping JSON (LLM call)
  → apply_mapping(ecc_df, mapping) → s4_df  (writes output_s4.csv)
  → [write_data — not yet implemented]
```

The LLM prompt (`map_data.py:MAPPING_PROMPT`) returns a structured JSON with two keys:
- `field_mappings` — per-field ECC→S/4HANA name, transformation type, and notes
- `consolidations` — multi-ECC-field merges (e.g. `Name1`+`Name2` → `OrganizationBPName1`)

`apply_mapping()` applies consolidations first, then individual field mappings with four transformation types: `date`, `boolean`, `zfill`, `none`.

## Environment Configuration

`.env` is gitignored. Required keys:

```
# SAP ECC OData
url=http://<host>:<port>/sap/opu/odata/sap/ZSIRA_TM_MIG_DETAILS_SRV/lfa1_detailsSet?$format=json
username1=...
password=...

# SAP AI Core (LLM)
AICORE_AUTH_URL=...
AICORE_CLIENT_ID=...
AICORE_CLIENT_SECRET=...
AICORE_RESOURCE_GROUP=...
AICORE_BASE_URL=...
LLM_DEPLOYMENT_ID=...
```

Note: `main.py` reads `url`, `username1`, `password` (not `USERNAME` / `ODATA_URL`).

## Dependencies

`requirements.txt` lists the core 14 packages. `req.txt` is the full pinned lockfile (56 packages) and is what `.venv` was built from. Key additions beyond the basics:

- `generative-ai-hub-sdk` / `ai-core-sdk` — SAP AI Core proxy for the LLM
- `langchain` / `langchain-core` — prompt templates and output parsers used in `map_data.py`
- `openai` — used internally by the SAP AI Core Langchain adapter

## Known Gaps

- `get_data.py` executes `fetch_odata_data()` at module level (no `if __name__ == "__main__"` guard), so importing the module triggers a live HTTP call.
