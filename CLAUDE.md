# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SAP ECC to S/4HANA data migration tool. Fetches vendor/supplier master data from an SAP ECC system via OData API, transforms it into a pandas DataFrame, and (eventually) loads it into S/4HANA via the SAP HANA database client (`hdbcli`).

## Running the Code

No build system — run Python files directly using the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
python functions/get_data.py
python functions/transform_data.py
```

## Architecture

ETL pipeline split across three modules in `functions/`:

| Module | Role | Status |
|---|---|---|
| `get_data.py` | Extract — HTTP GET to SAP ECC OData endpoint with Basic Auth | Working |
| `transform_data.py` | Transform — converts OData JSON response to pandas DataFrame, drops `__metadata` | Working |
| `write_data.py` | Load — write to S/4HANA via `hdbcli` | Empty stub |

**Key gap**: the three modules are not yet wired together. `get_data.py` prints results but doesn't return data to `transform_data.py`. A top-level orchestration script is needed.

## Environment Configuration

Credentials and the OData URL are loaded from `.env` via `python-dotenv`. The `.env` file is gitignored. Required keys:

```
ODATA_URL=http://<host>:<port>/sap/opu/odata/sap/ZSIRA_TM_MIG_DETAILS_SRV/lfa1_detailsSet
USERNAME=...
PASSWORD=...
```

## Key Dependencies

- `requests` — OData HTTP calls
- `pandas` — DataFrame transformation
- `hdbcli` — SAP HANA database client (for the write step)
- `python-dotenv` — loads `.env` credentials
