# Project Context — Bilal Ganj Parts Sourcing App

## What it does
Mechanic requests a car part via chat (web dashboard, mirrors WhatsApp flow) → LLM extracts structured fields → confirms → broadcasts to matching dealers via WhatsApp → dealers reply (available/price/genuine) → mechanic browses a catalog of qualifying offers, can chat/negotiate per-dealer → confirms one → ticket created, others auto-declined → chat stays open post-confirmation for delivery logistics.

## Stack
FastAPI + SQLite (`db_data/chat.db`), Meta WhatsApp Cloud API, LLM hosted on Colab + ngrok tunnel (rotates on restart — update `LLM_URL` env var each time). Runs in GitHub Codespaces, port 8000 forwarded publicly (must stay set to Public, resets to Private on rebuild).

## Folder structure
```
main.py                 — wiring only: routers, db.init_all(), stale-thread background task
config.py                — LLM_URL from env
whatsapp.py              — send_message(), extract_incoming() (from, text, msg_id)
memory.py                — with_memory decorator (legacy generic /chat only)
db/                       — one file per table, all using @contextmanager get_conn()
  connection.py, chat.py, shops.py, requests.py, dealer_threads.py, tickets.py, whatsapp.py
llm_service/              — call_llm(), extract_json() — shared by both services
mechanic_service/         — router.py, logic.py, prompts.py, validation.py, intent.py
dealer_service/           — router.py, logic.py, prompts.py, intent.py
routers/                  — webhook.py (WhatsApp in/out), chat.py (legacy generic), conversations.py, parts.py
static/                   — index.html (generic chat), whatsapp.html (debug thread viewer),
                            mechanic-dashboard.html (main UI)
```

## Schema (key tables)
- **part_requests**: id, mechanic_phone, car_model/variant/year, part_name, spec, genuine_pref, status, conversation (JSON log), has_unread, pending_dealer_question
  - status flow: COLLECTING_INFO → AWAITING_CONFIRMATION → BROADCASTING → REPORT_READY → TICKET_CREATED (also CANCELLED)
- **dealer_threads**: id, request_id (FK), shop_id/name/phone, status, is_genuine, price, conversation (JSON log), has_unread, pending_mechanic_question, alternative_offer, last_outbound_msg_id
  - status flow: CONTACTED → RESPONDED/REJECTED → PRICED → SELECTED/CLOSED (also NO_RESPONSE, AWAITING_MECHANIC_INPUT)
- **tickets**: id, request_id, dealer_thread_id, shop_name/phone, final_price, is_genuine
- **shops**: id, name, phone, parts (comma string, substring-matched — no fuzzy matching)

## Core flow logic
- One open request per phone at a time (`get_open_request` only matches COLLECTING_INFO/AWAITING_CONFIRMATION) — confirming frees the phone for a new request
- **Intent classification** (LLM call, before main handling) on both sides:
  - Mechanic: PROVIDING_FIELDS / ASKING_QUESTION / REQUESTING_CHANGE / (ANSWERING_DEALER_QUESTION — now dead code, see below)
  - Dealer: ANSWERING_AVAILABILITY / ASKING_QUESTION / OFFERING_ALTERNATIVE
- Dealer questions/alternatives surface ONLY inside that dealer's own thread chat (not the general request feed) — mechanic answers via the per-thread "Chat" box → `/dealer-threads/{id}/negotiate`
- General request feed only gets request-level "Update: ..." messages (price/availability), plus ticket creation notices
- Confirming an offer (`/dealer-threads/{id}/confirm`) creates a ticket, closes/declines all other threads for that request, but leaves the winning thread's chat open indefinitely for delivery coordination
- Stale dealer threads (CONTACTED, no reply, 6+ hours) auto-close to NO_RESPONSE via background task in `main.py`, checked every 15 min

## Known dead/inconsistent code
- `mechanic_service/router.py` still references `request.get("pending_dealer_question")` / ANSWERING_DEALER_QUESTION branch — obsolete since questions moved to per-thread only. Should be removed but wasn't confirmed deleted.
- Duplicate "Update:" messages bug seen once (5x same price update) — root cause not yet found, suspect polling or webhook retry re-triggering forward_update_to_mechanic. Not fixed.

## Fragile / unfinished (see leftovers.md for full list)
1. No broadcast dealer cap (contacts ALL matching shops, no limit)
2. Shop matching is exact-substring only, no fuzzy matching
3. No concurrency/race protection (simultaneous replies could interleave badly)
4. Only one open thread per dealer phone at a time (intentional scope decision — use separate WhatsApp numbers if a dealer needs parallel requests)
5. Intent classification adds 2x LLM calls per message — untested under real load, Colab/ngrok backend is the main reliability risk (dies on inactivity, timeouts)
6. No confidence handling in extraction — ambiguous mechanic input could be confidently mis-parsed

## Frontend notes
`mechanic-dashboard.html` — sidebar of requests, per-request chat + offers panel, per-dealer expandable "Chat" boxes (state tracked in JS `openThreadChats` Set to survive 4s polling rebuilds without flicker). Browser Notification API used for unread pings when tab unfocused.

## Ops gotchas hit repeatedly this project
- Codespace port visibility resets to Private on rebuild → webhook silently stops receiving (302 redirect to github login)
- ngrok URL for Colab LLM rotates every restart → update `LLM_URL` env, restart main.py
- WhatsApp access token expires ~24h (temporary token) → get System User permanent token to stop this
- Meta requires BOTH: WABA subscribed to app (`/subscribed_apps`) AND app subscribed to `messages` field (`/subscriptions?fields=messages`) — checking only the dashboard UI misses the second one
