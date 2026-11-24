# Rumor sources for Hot Stove GM trade intel

The owner's list (Nov 19, 2026). Use it when updating `intel.json` (who is on the block, what each club wants).

## Tier 1: national reporters (act on a single report)
- Jeff Passan (ESPN)
- Ken Rosenthal (The Athletic)
- Will Sammon (The Athletic)
- Others at the same level: Jon Heyman (New York Post), Mark Feinsand (MLB.com), Jon Morosi (MLB Network), Bob Nightengale (USA Today), Buster Olney and Jesse Rogers (ESPN), Robert Murray (FanSided), Joel Sherman (New York Post)

## Tier 2: team beat writers (act on a single report about their own club)
The beat writers for each of the 30 clubs at ESPN, The Athletic, MLB.com and the main local paper, East Coast, Midwest and West Coast alike.

## How to reach them
1. MLB Trade Rumors quotes these reporters with attribution; check it first.
2. Web search the reporter's name with the club or player and today's date.
3. X: reporters post there first, and fans often post the key line of a paywalled article. A fan post counts only when it names the reporter and outlet. Treat it as unconfirmed until MLB Trade Rumors, the reporter's own post or a second outlet matches; then use it.

## Rules
- Never guess. No report, no intel entry.
- Put the reporter and outlet in the note or `src` (for example "Rosenthal, The Athletic, Nov. 19").
- Do not copy paywalled text. One short line in our own words.
- "Wants a right-handed bat" or "needs a left-handed reliever" style details go in the club's `note`; `wants` keeps the position codes.
- **Owner notes come first.** An entry in `intel.json` with `"owner": true` is the owner's own read (for example: Miami picked up Sandy Alcantara's option in order to trade him, whatever the club says in public). Never change its status, note or `src`, and never remove it, because of public reporting or a club's public comments. Only a completed move (he is traded, signed elsewhere or retires) takes it off. If new reporting disagrees, leave the entry alone and say so in your summary.

## Untouchable is the owner's call (owner, 11/24/2026)
Never set a player's status to `untouchable` in `intel.json` from public reporting or a club's public comments. A club saying a player is not available, "not entertaining offers" or "not shopping him" is recorded as `"status": "listening", "price": "high", "denied": true`, with the quote in the note. `untouchable` is only for an entry the owner wrote (`"owner": true`) or a player with a full no-trade clause (`"ntc": true`). The app ignores any other `untouchable`.
