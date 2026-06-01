import json
import pandas as pd
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from llm.factory_llm import get_llm
from llm.model import map_data_llm  


MAPPING_PROMPT = ChatPromptTemplate.from_template("""
You are an SAP migration expert. Map the following SAP ECC vendor master (LFA1 table) fields
to their S/4HANA Business Partner (A2X API) equivalents.

ECC fields with sample values:
{field_info}

Return ONLY a valid JSON object with this exact structure:
{{
  "field_mappings": {{
    "<ECC_field>": {{
      "s4_field": "<S4HANA_field_name or null if unused>",
      "transformation": "<none|date|boolean|zfill>",
      "notes": "<brief reason>"
    }}
  }},
  "consolidations": {{
    "<s4_target_field>": ["<ecc_field1>", "<ecc_field2>"]
  }}
}}

Rules:
- Use S/4HANA Business Partner A2X API field names exactly.
- transformation "date"    → convert SAP /Date(ms)/ or string date to YYYY-MM-DD.
- transformation "boolean" → map True/False to SAP "X"/"" convention.
- transformation "zfill"   → zero-pad to standard SAP length.
- transformation "none"    → copy value as-is.
- Use "consolidations" when multiple ECC fields merge into one S/4HANA field
  (e.g. Name1+Name2 → OrganizationBPName1). Do NOT repeat those fields in field_mappings.
- Set s4_field to null for internal/technical ECC fields that have no S/4HANA equivalent.
""")


def _build_field_info(df: pd.DataFrame) -> str:
    field_info = {}
    for col in df.columns:
        non_null = df[col].dropna()
        sample = str(non_null.iloc[0]) if not non_null.empty else ""
        field_info[col] = sample
    return json.dumps(field_info, indent=2)


def get_field_mapping(df: pd.DataFrame) -> dict:
    llm = map_data_llm
    chain = MAPPING_PROMPT | llm | JsonOutputParser()
    mapping = chain.invoke({"field_info": _build_field_info(df)})
    return mapping


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    s4_df = pd.DataFrame()
    field_mappings = mapping.get("field_mappings", {})
    consolidations = mapping.get("consolidations", {})
    consolidated_ecc_fields = {f for fields in consolidations.values() for f in fields}

    # Consolidate multiple ECC fields into one S/4HANA field
    for s4_field, ecc_fields in consolidations.items():
        available = [f for f in ecc_fields if f in df.columns]
        if available:
            s4_df[s4_field] = df[available].apply(
                lambda row: " ".join(
                    str(v).strip() for v in row if pd.notna(v) and str(v).strip()
                ),
                axis=1,
            )

    # Map individual fields
    for ecc_field, info in field_mappings.items():
        if ecc_field in consolidated_ecc_fields or ecc_field not in df.columns:
            continue
        if info is None or info.get("s4_field") is None:
            continue

        s4_field = info["s4_field"]
        transformation = info.get("transformation", "none")

        if transformation == "date":
            s4_df[s4_field] = pd.to_datetime(df[ecc_field], errors="coerce").dt.strftime("%Y-%m-%d")
        elif transformation == "boolean":
            s4_df[s4_field] = df[ecc_field].map({True: "X", False: "", "True": "X", "False": ""})
        elif transformation == "zfill":
            s4_df[s4_field] = df[ecc_field].astype(str).str.zfill(10)
        else:
            s4_df[s4_field] = df[ecc_field]

    return s4_df
