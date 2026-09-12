# Leftovers / Known Issues

## Fragile — will break in real conversations

1. **[RESOLVED] Dealer Conversation Memory.** Multi-turn dealer messages merged across history. If price is given in one message and genuine/aftermarket in another, state merges cumulatively.
2. **[RESOLVED] Multi-turn dealer follow-up.** Classifier and parser receive previous system message and thread state context.
3. **Shop matching is exact-substring only.** "transmission" ≠ "gearbox" ≠ "gear box" — mismatched wording means a dealer silently never gets contacted, no error.
4. **Mechanic confirmation is fuzzy "yes"-contains only.** Any correction re-runs extraction on full conversation history, which can silently drop previously-set fields.
5. **[RESOLVED] Dealer saying "no, don't have it".** Correctly marked REJECTED, closes follow-up, and notifies mechanic.
6. **[RESOLVED] Aggregated Report Generation.** Generates comprehensive quote reports (best offer, genuine vs aftermarket, dealers breakdown) and updates request status to REPORT_READY.
7. **No order-placing flow.** Delivery address, payment details, confirming the winning dealer — not built.
8. **No confidence/ambiguity handling in extraction.** Ambiguous mechanic messages ("the usual bumper thing") may get confidently mis-extracted rather than flagged as unclear.
9. **No concurrency handling.** Two near-simultaneous dealer replies, or two rapid mechanic messages, could interleave badly during conversation JSON read-modify-write (not atomic).
10. **[RESOLVED] Main Chat Routing to Dealers.** Mechanic messages in broadcasting/report stage now broadcast to all active dealers.
11. **[RESOLVED] Unprotected WhatsApp Outbound.** Outbound Meta API calls are protected with try-except, timeout, and pre-persistence in SQLite so WhatsApp errors do not drop messages.