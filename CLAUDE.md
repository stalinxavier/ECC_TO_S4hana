# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SAP ECC to S/4HANA data migration tool. Fetches vendor/supplier master data (LFA1 table) from an SAP ECC system via OData API, transforms it, uses an LLM (via SAP AI Core) to generate ECC→S/4HANA field mappings, and writes the result to S/4HANA via the Business Partner OData API.

## Running the Code

No build system — run Python files directly using the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
python main.py        # direct ETL pipeline (no interaction)
python agent.py       # LangChain agent pipeline (also non-interactive; this is the Docker CMD)
```

Individual stages can also be run standalone:

```powershell
python func/get_data.py        # prints raw OData JSON (triggers live HTTP call on import — see Known Issues)
python func/transform_data.py  # writes output1.csv
```

## Architecture

Two execution paths share the same four ETL stages:

- **`main.py`** — calls ETL functions directly in sequence
- **`agent.py`** — LangChain OpenAI tools agent wrapping the same stages via `func/tools.py`; used as the Docker `CMD`

### `func/` — ETL stages

| Module | Role |
|---|---|
| `get_data.py` | Extract — HTTP GET to SAP ECC OData endpoint with Basic Auth |
| `transform_data.py` | Transform — JSON → pandas DataFrame; cleans dates, strings, booleans, zero-padding |
| `map_data.py` | Map — sends ECC column names + sample values to LLM; receives JSON mapping; applies it to produce S/4HANA-ready DataFrame |
| `write_data.py` | Load — POSTs rows to S/4HANA Business Partner OData API with CSRF token handling; reports created/skipped/failed counts |
| `tools.py` | LangChain `@tool` wrappers around the four stages above, plus `preview_data` and `get_pipeline_status`; shares state via module-level `_state` dict |

### `llm/` — LLM integration

- `factory_llm.py` — instantiates `ChatOpenAI` via `gen-ai-hub` SAP AI Core proxy; reads all `AICORE_*` env vars
- `model.py` — single shared `map_data_llm` instance (temperature=0) imported by `map_data.py` and `agent.py`

### Data flow

```
SAP ECC OData
  → fetch_odata_data()             → raw JSON
  → convert_to_dataframe()         → ecc_df  (writes output1.csv / output_ecc.csv)
  → get_field_mapping(ecc_df)      → mapping JSON (LLM call)
  → apply_mapping(ecc_df, mapping) → s4_df   (writes output_s4.csv)
  → write_to_s4hana(s4_df)         → POSTs to /A_BusinessPartner OData endpoint
```

The LLM prompt (`map_data.py:MAPPING_PROMPT`) returns structured JSON with two keys:
- `field_mappings` — per-field ECC→S/4HANA name, transformation type (`date` | `boolean` | `zfill` | `none`), and notes
- `consolidations` — multi-ECC-field merges (e.g. `Name1`+`Name2` → `OrganizationBPName1`)

`apply_mapping()` applies consolidations first (space-joined), then individual field mappings. Boolean fields use SAP convention: `True`→`"X"`, `False`→`""`.

`write_to_s4hana()` deep-inserts address fields into a nested `to_BusinessPartnerAddress` navigation property. It handles 201 (created), 409 (conflict/already exists), and other responses separately. SSL verification is disabled.

## Environment Configuration

`.env` is gitignored. Required keys:

```
# SAP ECC OData
url=http://<host>:<port>/sap/opu/odata/sap/ZSIRA_TM_MIG_DETAILS_SRV/lfa1_detailsSet?$format=json
username1=...
password=...

# SAP S/4HANA OData (write_data.py)
S4_URL=https://<host>/sap/opu/odata/sap/API_BUSINESS_PARTNER
S4_USERNAME=...
S4_PASSWORD=...

# SAP AI Core (LLM)
AICORE_AUTH_URL=...
AICORE_CLIENT_ID=...
AICORE_CLIENT_SECRET=...
AICORE_RESOURCE_GROUP=...
AICORE_BASE_URL=...
LLM_DEPLOYMENT_ID=...
```

Note: ECC credentials use `url`, `username1`, `password` (not `USERNAME` / `ODATA_URL`).

## Dependencies

`requirements.txt` — core package list. `reqq.txt` — full pinned lockfile (what `.venv` was built from). Key additions beyond the basics:

- `generative-ai-hub-sdk` / `ai-core-sdk` — SAP AI Core proxy for the LLM
- `langchain` / `langchain-core` — agent framework, prompt templates, JSON output parser
- `openai` — used internally by the SAP AI Core LangChain adapter

## Known Issues

- `get_data.py` executes `fetch_odata_data()` at module level (no `if __name__ == "__main__"` guard), so importing the module triggers a live HTTP call to the ECC endpoint.
- `map_data.py` has unused imports: `ChatOpenAI` and `get_llm` are imported but `map_data_llm` from `llm/model.py` is what's actually used.
