EXTRACT_PROMPT = """You are extracting a car part request from a conversation.
Required fields: car_model, car_variant, car_year, part_name, spec, genuine_pref (genuine/aftermarket/either).

Conversation so far:
{conversation}

Return ONLY a JSON object with any of these fields you can determine. Use null for fields not mentioned.
Example: {{"car_model": "Honda City", "car_variant": null, "car_year": null, "part_name": "front bumper", "spec": null, "genuine_pref": null}}
JSON:"""

CLARIFY_PROMPT = """A mechanic is requesting a car part. These fields are still missing: {missing}.
Ask ONE short, natural message asking for just these missing details. Don't repeat what's already known.
Missing fields: {missing}
Message:"""
