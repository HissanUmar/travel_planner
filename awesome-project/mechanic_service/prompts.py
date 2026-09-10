EXTRACT_PROMPT = """You are extracting a car part request from a conversation.
Required fields: car_model, car_variant, car_year, part_name, spec, genuine_pref (genuine/aftermarket/either).

Conversation so far:
{conversation}

Return ONLY a JSON object with any of these fields you can determine. Use null for fields not mentioned.
JSON:"""

CLARIFY_PROMPT = """A mechanic is requesting a car part. These fields are still missing: {missing}.
Ask ONE short, natural message asking for just these missing details.
Message:"""

CLASSIFY_PROMPT = """A mechanic is messaging our car-parts sourcing system. Current request state:
Status: {status}
Known so far: car_model={car_model}, part_name={part_name}, missing fields: {missing}
Is there a dealer question waiting for the mechanic's answer right now? {has_pending_question}

Their message: "{text}"

Classify this message as ONE of:
- PROVIDING_FIELDS (giving car/part details, answering a clarification)
- ASKING_QUESTION (asking about status, process, or general question — not providing new part details)
- REQUESTING_CHANGE (trying to change already-confirmed details of a request that's already broadcasting)
- ANSWERING_DEALER_QUESTION (answering the pending dealer question shown above, if one exists)

Reply with ONLY the label.
Label:"""

ANSWER_QUESTION_PROMPT = """You are a helpful assistant for a mechanic using a car-parts sourcing platform. Answer their question using ONLY the context below — don't invent information.

Request status: {status}
Part requested: {part_name} for {car_model} {car_variant} ({car_year})
Dealers contacted: {dealer_summary}

Mechanic's question: "{text}"

Answer briefly and honestly. If you don't have the information, say so plainly.
Answer:"""