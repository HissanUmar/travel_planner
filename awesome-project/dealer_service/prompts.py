def build_outreach_message(request: dict) -> str:
    return (
        f"Hi, a mechanic is looking for a part:\n\n"
        f"Car: {request['car_model']} {request['car_variant']} ({request['car_year']})\n"
        f"Part: {request['part_name']}\n"
        f"Spec: {request['spec']}\n"
        f"Preference: {request['genuine_pref']}\n\n"
        f"Do you have this in stock? Please reply with availability and price."
    )

def build_parse_prompt(conversation: list) -> str:
    convo_text = "\n".join(f"{m['role']}: {m['text']}" for m in conversation)
    return f"""This is a WhatsApp conversation between our system (llm) and a car parts dealer, checking part availability.

Conversation so far:
{convo_text}

Based on the ENTIRE conversation above, extract the current known state as JSON:
- available: true/false/null
- is_genuine: true/false/null
- price: number/null (in PKR)
- needs_followup: true/false
- followup_question: string/null

If available is false, set needs_followup to false.
JSON:"""

def build_dealer_persona_prompt(shop: dict, text: str) -> str:
    return f"""You are the assistant for a car parts sourcing platform based in Bilal Ganj, connecting mechanics with parts dealers. You're speaking with {shop['name']}, one of our registered dealer partners — not a customer.

You're knowledgeable about the auto parts market: genuine vs aftermarket pricing, common part names/specs, and how sourcing requests work on this platform. Speak like a professional partner-support contact, not a generic assistant.

Their message: "{text}"

Reply helpfully and briefly:"""