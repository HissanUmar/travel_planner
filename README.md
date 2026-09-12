# Bilal Ganj Parts App — Setup Guide

## Architecture

```
Mechanic/Shop (WhatsApp) <--> Meta Cloud API <--> main.py (Codespaces) <--> LLM server (Colab, via ngrok)
                                                        |
                                                   SQLite (db_data/chat.db)
```

Two separate servers, two separate public URLs:
1. **LLM server** — runs in Colab, exposed via ngrok (`/generate`, `/embed`)
2. **App server** — `main.py`, runs in GitHub Codespaces, exposed via Codespaces port forwarding (`/chat`, `/webhook`, `/request-part`, `/conversations`)

---

## 1. Colab LLM Server + ngrok

**Every time the Colab notebook restarts, the ngrok URL rotates.** This breaks the app until updated.

### Setup
- Colab notebook runs the LLM (`llm.invoke`) and embedder, exposed via `pyngrok`
- Requires an ngrok authtoken (free at ngrok.com), stored in Colab as a secret: `NGROK_AUTHTOKEN`
- Free ngrok tier = 1 tunnel at a time

### After every Colab restart
1. Rerun the Colab cell — note the printed `Public URL`
2. Update the app's `LLM_URL`:
   ```bash
   export LLM_URL="https://<new-ngrok-url>.ngrok-free.dev/generate"
   ```
3. Restart `main.py` (env vars are read once at startup)

### Verify it's alive
```bash
curl -X POST https://<ngrok-url>.ngrok-free.dev/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "hello"}'
```
Should return JSON with a `response` key. Empty response / 404 / connection error = Colab session died or URL is stale.

---

## 2. GitHub Codespaces — Port Forwarding

The app server (`main.py`) needs a public HTTPS URL for Meta to reach `/webhook`. Codespaces provides this via port forwarding — no second ngrok needed.

### Setup
1. Run `python main.py` (listens on port 8000)
2. Open the **Ports** tab (bottom panel, next to Terminal)
3. Port `8000` should auto-appear
4. Right-click → **Port Visibility** → **Public**
   - ⚠️ **Private is the default and will silently break incoming webhooks** — requests get redirected to a GitHub login page (`302` to `github.dev/pf-signin`), which Meta cannot complete
5. Copy the generated URL: `https://<codespace-name>-8000.app.github.dev`

### Known issue: URL + visibility both reset
Codespace restarts/rebuilds can:
- Change the forwarded URL entirely
- Reset port visibility back to Private

**After any Codespace restart, always re-check both** before assuming the webhook is broken.

### Verify it's reachable
```bash
curl "https://<codespace-url>/webhook?hub.mode=subscribe&hub.verify_token=<your-verify-token>&hub.challenge=999"
```
Should return `999` directly. A `302 redirect` response = visibility is Private, not Public.

**Long-term fix:** if this instability becomes a problem, move `main.py` off Codespaces to a host with a fixed URL (Railway, Render, a small VPS).

---

## 3. Meta WhatsApp Cloud API — Requirements

### Accounts/IDs needed
| Item | Where to find it |
|---|---|
| App Secret | Meta for Developers → your app → Settings → Basic |
| App ID | Same page as above |
| Phone Number ID | WhatsApp → API Setup |
| WhatsApp Business Account ID (WABA ID) | WhatsApp → API Setup (labeled separately from Phone Number ID) |
| Access Token | WhatsApp → API Setup (temporary, ~24hr) or Business Settings → System Users (permanent — recommended) |

### Env vars used by `whatsapp.py`
```
WA_PHONE_NUMBER_ID=<phone number id>
WA_ACCESS_TOKEN=<access token>
WA_VERIFY_TOKEN=<any string you invent, e.g. "mysecret123">
```

### One-time dashboard config
1. **WhatsApp → Configuration → Webhook**
   - Callback URL: `https://<codespace-url>/webhook`
   - Verify Token: must exactly match `WA_VERIFY_TOKEN`
   - Click "Verify and Save" (only works if the app server is running and reachable at that moment)

2. **Subscribe the WABA to your app** (easy to miss — doing step 1 alone is not enough):
   ```bash
   curl -X POST "https://graph.facebook.com/v20.0/<WABA_ID>/subscribed_apps" \
     -H "Authorization: Bearer <access_token>"
   ```
   Should return `{"success": true}`.

3. **Subscribe the app to the `messages` field** (also easy to miss):
   ```bash
   curl -X POST "https://graph.facebook.com/v20.0/<APP_ID>/subscriptions" \
     -H "Authorization: Bearer <app_access_token>" \
     -d "object=whatsapp_business_account" \
     -d "callback_url=https://<codespace-url>/webhook" \
     -d "verify_token=<your-verify-token>" \
     -d "fields=messages"
   ```
   App access token format: `<APP_ID>|<APP_SECRET>`, or generate via Graph API Explorer.

   Verify it worked:
   ```bash
   curl -X GET "https://graph.facebook.com/v20.0/<APP_ID>/subscriptions?fields=fields" \
     -H "Authorization: Bearer <app_access_token>"
   ```
   Should list `"fields": ["messages"]` — empty `data` means webhooks won't fire even if everything else looks correct.

### Test mode restrictions (no Business Verification)
- Can only **send** to numbers explicitly added under WhatsApp → API Setup → recipient list
- Each test recipient must verify via a code sent to their WhatsApp
- **Receiving** messages has no such restriction — anyone can message your test number and trigger the webhook

### 24-hour session window
- Free-form text can only be sent to a number that has messaged you within the last 24 hours
- Outside that window, only pre-approved **template messages** can initiate contact
- Currently **not implemented** in this app — all outbound messages assume an open window (works for testing where you message yourself first; will fail for cold-contacting real shop owners without templates)

### Common errors and what they mean
| Error | Cause |
|---|---|
| `401 Authentication Error` (code 190) | Access token expired — get a new one, or switch to a permanent System User token |
| `(#131030) Recipient phone number not in allowed list` | Number not added as a test recipient |
| `400` on template send with real content but no delivery | Recipient hasn't opened a 24hr window (hasn't messaged you) and you sent free text, not a template |
| Webhook never fires (no `POST /webhook` in logs) | WABA not subscribed to app, OR app not subscribed to `messages` field — check both separately (see steps 2 & 3 above) |
| Duplicate incoming messages logged | Meta retries webhook calls that don't return `200` fast enough or throw errors — handled via `msg_id` deduplication in `db/whatsapp.py` |

---

## Quick restart checklist (after any break)

1. Colab LLM server alive? → test `/generate` directly with curl
2. `LLM_URL` env var updated to current ngrok URL?
3. Codespace port 8000 set to **Public**?
4. Meta webhook Callback URL matches current Codespace URL?
5. Access token still valid (not expired)?
