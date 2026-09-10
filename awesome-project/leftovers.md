# Leftovers / Known Issues

## Fragile — will break in real conversations

1. **No conversation memory in dealer replies.** Each dealer message parsed in isolation — "yes I have it" then "14500" separately never merges. *(fixing now)*
2. **Multi-turn dealer follow-up not handled.** If LLM asks a clarifying question, the dealer's answer is parsed standalone with no context of what was asked.
3. **Shop matching is exact-substring only.** "transmission" ≠ "gearbox" ≠ "gear box" — mismatched wording means a dealer silently never gets contacted, no error.
4. **Mechanic confirmation is fuzzy "yes"-contains only.** Any correction re-runs extraction on full conversation history, which can silently drop previously-set fields.
5. **Dealer saying "no, don't have it" isn't handled.** No check for `available: false` — thread stays open, LLM may still ask a followup or just acknowledge. *(fixing now)*
6. **No report generation.** After dealers respond, nothing aggregates price/genuine/availability back into a report for the mechanic. Core to original spec, not built yet.
7. **No order-placing flow.** Delivery address, payment details, confirming the winning dealer — not built.
8. **No confidence/ambiguity handling in extraction.** Ambiguous mechanic messages ("the usual bumper thing") may get confidently mis-extracted rather than flagged as unclear.
9. **No concurrency handling.** Two near-simultaneous dealer replies, or two rapid mechanic messages, could interleave badly during conversation JSON read-modify-write (not atomic).

## Order to harden (suggested)
1 & 5 first (most likely to break in any real multi-message exchange) → 6 & 7 (missing features, not bugs) → 2, 3, 4, 8, 9 as they surface.