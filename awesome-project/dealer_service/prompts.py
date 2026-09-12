def build_outreach_message(request: dict) -> str:
    return (
        f"Hi, a mechanic is looking for a part:\n\n"
        f"Car: {request['car_model']} {request['car_variant']} ({request['car_year']})\n"
        f"Part: {request['part_name']}\n"
        f"Spec: {request['spec']}\n"
        f"Preference: {request['genuine_pref']}\n\n"
        f"Do you have this in stock? Please reply with availability and price."
    )

def build_parse_prompt(conversation: list, current_state: dict = None) -> str:
    convo_text = "\n".join(f"{m['role']}: {m['text']}" for m in conversation)
    state_note = ""
    if current_state:
        price_val = current_state.get('price')
        gen_val = current_state.get('is_genuine')
        state_note = f"Previously established in this thread:\n- Price: {price_val if price_val is not None else 'unknown'}\n- Genuine/Aftermarket: {gen_val if gen_val is not None else 'unknown'}\n\n"

    return f"""This is a WhatsApp conversation between our sourcing bot (llm) and a car parts dealer.
{state_note}Full conversation history:
{convo_text}

Based on the ENTIRE conversation history, extract the cumulative current status as JSON:
- available: true/false/null (set false if dealer says they don't have it, out of stock, nahi hai, etc.)
- is_genuine: true (genuine/original)/false (aftermarket/chinese/copy)/null
- price: number/null (in PKR, digits only, e.g. 14500)

If available is false, set price to null and is_genuine to null.
JSON:"""

def build_dealer_persona_prompt(shop: dict, text: str) -> str:
    return f"""You are the assistant for a car parts sourcing platform based in Bilal Ganj, connecting mechanics with parts dealers. You're speaking with {shop['name']}, one of our registered dealer partners — not a customer.

You're knowledgeable about the auto parts market: genuine vs aftermarket pricing, common part names/specs, and how sourcing requests work on this platform. Speak like a professional partner-support contact, not a generic assistant.

Their message: "{text}"

Reply helpfully and briefly:"""

def build_dealer_classify_prompt(request: dict, thread: dict, text: str, last_system_msg: str = None) -> str:
    context_line = f"Our last message to the dealer was: \"{last_system_msg}\"\n" if last_system_msg else ""
    return f"""A dealer is replying on WhatsApp about a car part request:
Part requested: {request.get('part_name')} for {request.get('car_model')} {request.get('car_variant')} ({request.get('car_year')})
Preference: {request.get('genuine_pref')}

{context_line}Their reply: "{text}"

Classify this reply as ONE of:
- ANSWERING_AVAILABILITY (stating if they have it, answering a price/genuine question, or giving quotes)
- ASKING_QUESTION (asking a clarifying question back that requires the mechanic's answer)
- OFFERING_ALTERNATIVE (offering a different part/spec/model than what was requested)

Reply with ONLY the label.
Label:"""

def build_extract_alternative_prompt(text: str) -> str:
    return f"""A dealer offered an alternative to what was requested. Their message: "{text}"

Extract as JSON:
- description: string (what they're offering instead)
- price: number/null

JSON:"""