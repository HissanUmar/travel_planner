import re

VALID_GENUINE = {"genuine", "aftermarket", "either"}

def normalize_genuine_pref(value: str):
    if not value:
        return None
    value = value.lower().strip()
    if "genuine" in value or "original" in value or "oem" in value:
        return "genuine"
    if "after" in value or "local" in value or "copy" in value:
        return "aftermarket"
    if "either" in value or "any" in value or "doesn't matter" in value or "dont matter" in value:
        return "either"
    return None

def validate_year(value: str):
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group())
    if 1980 <= year <= 2027:
        return str(year)
    return None

def validate_fields(fields: dict) -> dict:
    """Returns only the fields that pass validation. Invalid ones are dropped (treated as still missing)."""
    validated = {}

    if fields.get("car_model"):
        validated["car_model"] = fields["car_model"].strip()
    if fields.get("car_variant"):
        validated["car_variant"] = fields["car_variant"].strip()
    if fields.get("part_name"):
        validated["part_name"] = fields["part_name"].strip()
    if fields.get("spec"):
        validated["spec"] = fields["spec"].strip()

    year = validate_year(fields.get("car_year"))
    if year:
        validated["car_year"] = year

    genuine = normalize_genuine_pref(fields.get("genuine_pref"))
    if genuine:
        validated["genuine_pref"] = genuine

    return validated
