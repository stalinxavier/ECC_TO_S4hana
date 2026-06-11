import os
import re
import warnings
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

_BP_SERVICE = "/sap/opu/odata/sap/API_BUSINESS_PARTNER"
_BP_ENTITY  = "A_BusinessPartner"

# Whitelist of fields valid directly on A_BusinessPartner (from SAP Business Accelerator Hub).
# Any field the LLM maps that is NOT in this set is silently dropped.
_VALID_BP_FIELDS = {
    "AcademicTitle", "AuthorizationGroup", "BusinessPartnerCategory",
    "BusinessPartnerType", "BusinessPartnerIDByExtSystem",
    # BusinessPartnerGrouping excluded — codes are system-specific customizing, ECC values won't match S/4HANA
    "BusinessPartnerIsBlocked", "BusinessPartnerOccupation", "BusinessPartnerPrintFormat",
    "BusinessPartnerBirthDateStatus", "BusinessPartnerBirthplaceName",
    "BusinessPartnerBirthName", "BusinessPartnerSupplementName", "BusinessPartnerDeathDate",
    "BPDataControllerIsNotRequired", "BusPartMaritalStatus", "BusPartNationality",
    "CorrespondenceLanguage", "FirstName", "GenderCodeName",
    "GroupBusinessPartnerName1", "GroupBusinessPartnerName2",
    "Industry", "Initials", "InternationalLocationNumber1", "InternationalLocationNumber2",
    "InternationalLocationNumber3", "IsFemale", "IsMale", "IsMarkedForArchiving",
    "IsNaturalPerson", "IsSexUnknown", "Language", "LastName", "LastNamePrefix",
    "LastNameSecondPrefix", "MiddleName", "NameCountry", "NameFormat",
    # LegalForm intentionally excluded — requires SAP key codes (e.g. "AG", "GmbH"), LLM sends invalid values
    # FormOfAddress intentionally excluded — requires SAP key codes (e.g. "0001"), LLM sends free text
    "NaturalPersonEmployerName", "OrganizationBPName1", "OrganizationBPName2",
    "OrganizationBPName3", "OrganizationBPName4", "OrganizationFoundationDate",
    "OrganizationLiquidationDate", "PersonFullName", "SearchTerm1", "SearchTerm2",
    "AdditionalLastName", "BirthDate", "TradingPartner",
}

# Build a lowercase → original-case lookup for case-insensitive matching
_VALID_BP_FIELDS_LOWER = {f.lower(): f for f in _VALID_BP_FIELDS}

# Address fields live on the to_BusinessPartnerAddress navigation property.
_ADDRESS_FIELDS = {
    "country", "cityname", "district", "pobox", "poboxpostalcode",
    "postalcode", "region", "streetname", "poboxdeviatingcityname",
    "taxjurisdiction", "transportationzone",
}

_MAX_LEN = {
    "searchterm1": 20,
    "searchterm2": 20,
}


def _get_session() -> tuple[requests.Session, str]:
    base_url = os.getenv("S4_URL").rstrip("/")
    session = requests.Session()
    session.auth = (os.getenv("S4_USERNAME"), os.getenv("S4_PASSWORD"))
    session.headers.update({
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    })
    session.verify = False
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    resp = session.get(
        f"{base_url}{_BP_SERVICE}/{_BP_ENTITY}?$top=1",
        headers={"X-CSRF-Token": "Fetch"},
    )
    resp.raise_for_status()
    session.headers.update({"X-CSRF-Token": resp.headers.get("X-CSRF-Token", "")})
    return session, base_url


def _build_payload(row: dict) -> dict:
    bp   = {"BusinessPartnerCategory": "2"}  # "2" = Organization (company/vendor)
    addr = {}

    for key, raw in row.items():
        try:
            if pd.isna(raw):
                continue
        except (TypeError, ValueError):
            pass

        key_lower = str(key).strip().lower()
        value = str(raw).strip()

        if not value or value.lower() == "nan":
            continue

        if key_lower in _ADDRESS_FIELDS:
            if key_lower == "country":
                value = value.upper()
                if not re.match(r"^[A-Z]{2,3}$", value):
                    continue
            addr[_VALID_BP_FIELDS_LOWER.get(key_lower, key)] = value
            continue

        # Only send fields that exist on A_BusinessPartner
        canonical = _VALID_BP_FIELDS_LOWER.get(key_lower)
        if canonical is None:
            continue

        max_len = _MAX_LEN.get(key_lower)
        if max_len and len(value) > max_len:
            value = value[:max_len]

        bp[canonical] = value

    # Nest address fields under the navigation property for a deep insert
    if addr:
        bp["to_BusinessPartnerAddress"] = {"results": [addr]}

    return bp


def write_to_s4hana(df: pd.DataFrame) -> None:
    if df.empty:
        print("write_to_s4hana: DataFrame is empty — nothing to write.")
        return

    # Guard against any duplicates that survived earlier stages
    bp_id_col = next((c for c in df.columns if c.lower() in ("businesspartneridbyextsystem", "lifnr")), None)
    if bp_id_col:
        before = len(df)
        df = df.drop_duplicates(subset=[bp_id_col], keep="first")
        removed = before - len(df)
        if removed:
            print(f"write_to_s4hana: dropped {removed} duplicate row(s) by {bp_id_col} before posting.")

    session, base_url = _get_session()
    url = f"{base_url}{_BP_SERVICE}/{_BP_ENTITY}"

    created  = 0
    already  = 0  # 409 — record exists in S/4HANA
    skipped  = 0  # missing required fields
    failed   = 0

    for _, row in df.iterrows():
        payload = _build_payload(row.to_dict())

        if not payload.get("OrganizationBPName1"):
            print(f"write_to_s4hana: skipping row — OrganizationBPName1 is missing or empty (row data: {dict(list(row.items())[:3])}...)")
            skipped += 1
            continue

        resp = session.post(url, json=payload)

        if resp.status_code == 201:
            created += 1
        elif resp.status_code == 409:
            already += 1
        else:
            failed += 1
            print(f"write_to_s4hana: POST failed [{resp.status_code}] — {resp.text[:200]}")

    print(
        f"write_to_s4hana: {created} created, {already} already in S/4HANA (409), "
        f"{skipped} skipped (missing name), {failed} failed — total {len(df)} records"
    )
