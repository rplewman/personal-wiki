---
title: Draft Copilot
project: Draft Copilot
doc_type: project-summary
status: complete
built: 2026-09
written: 2026-09-29
source: Written after the build from the app code (Draft App/index.html, server.js) and the build conversation
redactions: "League, draft IDs, team name, draft slot, drafted roster and other managers omitted"
tags: [draft-copilot, fantasy-football, sleeper-api, rankings, personal-project]
---

# Draft Copilot

A small local web app that ran alongside a live Sleeper fantasy football draft. It tracked every pick in real time and recommended who to take next. It was built in one session with Claude Code on the day of the draft in September 2026.

## Objective

The goal was a tool to use during a **12-team, full-PPR snake draft** on Sleeper, to make sure that:

1. **The right players get drafted.** Recommendations should come from expert consensus rankings, not Sleeper's ADP (average draft position), which reflects what the crowd picks rather than how good players are.
2. **Positional gaps get filled.** The app should know which starting slots are still empty and point toward them.
3. **Each pick is a good pick for that round**, not just the best player left. For example, is the 11th-ranked RB a better choice at pick 2.10 than the top-ranked TE?
4. **There's quick context on each player**: a short upside/downside note and any injury status.

## Approach

### Choosing the architecture
Two ideas were considered:

- **Screenshot app.** Upload a screenshot of the draft board and get a suggestion. This was rejected because reading text from images is unreliable and breaks whenever Sleeper changes its layout.
- **Live companion.** This turned out to be the *easier* option. Sleeper has a **public, no-login JSON API** for drafts:
  - `GET https://api.sleeper.app/v1/draft/{draft_id}` returns draft settings, roster slots and scoring.
  - `GET https://api.sleeper.app/v1/draft/{draft_id}/picks` returns every pick made so far.

The companion won. It was built as a **single `index.html` file** with the rankings data embedded: no build step and no dependencies. A tiny Node static server (`server.js`) serves it at `http://localhost:8931`. Vercel hosting was considered and dropped in favour of running it locally.

### Rankings dataset
The default rankings deliberately avoid Sleeper ADP. They blend two expert sources, both confirmed to be **full-PPR** lists:

| Source | Coverage | Weight |
|---|---|---|
| FantasyPros consensus (about 128 experts, PPR cheat sheet) | Top 100 | 0.6 |
| ESPN Field Yates PPR rankings | Top 160 | 0.4 |

- A player on both lists gets `FantasyPros_rank × 0.6 + ESPN_rank × 0.4`, and the list is re-sorted by that blended score. FantasyPros gets more weight because it is already an average of many experts.
- A player on only one list (mostly ESPN's 101–160 range) keeps that source's rank.
- The result is about 160 players, each with an overall rank, position rank and each source's individual rank.
- It's a **static snapshot** from draft day and does not refresh automatically.

**Why it differs from ADP:** ADP is crowd behaviour. It captures name recognition, hype and slow reactions to news. Expert rankings are considered opinions of each player's season value, so they usually react to trades and role changes before ADP does.

## Features

- **Live polling:** the app fetches picks every 3 seconds. Sleeper's CDN caches the picks endpoint for up to 30 seconds (`s-maxage=30`), so a new pick can take up to about 30 seconds to appear. That's well inside a 60-second pick clock.
- **Best Available:** consensus rankings with anyone already drafted by *any* team removed. It can be filtered by position and searched.
- **My Team and Needs tracker:** your own picks are detected automatically and slotted into QB/RB/WR/TE/FLEX/K/DEF, with each starting slot shown as filled or still open.
- **Value sort:** the default sort order, which adjusts consensus rank for position scarcity (see below). You can switch back to raw consensus rank.
- **Top recommendation banner:** the single best-value pick available right now (skipping K/DST), tagged "fills a need" where it applies.
- **Needs highlight:** a green edge on Best Available rows for positions (or flex-eligible positions) you still need.
- **VALUE / REACH tags:** these compare a player's consensus rank with the current pick number. They appear on Best Available before you pick, and on the Live Picks feed (last 25 picks) afterwards.
- **Player notes and injury badges:** a one-line upside/downside note per player, plus live injury status (Questionable, IR, PUP) from Sleeper's player database.
- **Bye-week clash warnings:** a flag on any available player whose bye week matches a player already on your roster.
- **Strategy panel:** short guidance on draft order. Prioritise RB/WR early, wait on QB unless an elite rushing QB falls, take either an elite TE or wait, and leave K/DST until last.
- **Settings:** set the draft ID and your draft slot. Both are saved in `localStorage`, so they survive a page refresh.

## The Value Model

Raw consensus rank answers "who is the better player?", but not "who is the better pick right now?" The value model adds position scarcity as a *secondary nudge*:

```text
scarcity   = POS_SLOPE[pos] × (REPLACEMENT_RANK[pos] − position_rank)
blended    = −consensus_rank + 0.4 × scarcity

REPLACEMENT_RANK = { QB:14, RB:34, WR:40, TE:14, K:12, DST:12 }
POS_SLOPE        = { QB:0.6, RB:1.3, WR:1.0, TE:1.0, K:0.3, DST:0.3 }
```

- **Replacement rank** is roughly how deep you can go at a position before you're down to players any team could pick up on waivers.
- **Slope** is how much each step down the position ranks costs. RB drops off sharply after the true workhorse backs (1.3). WR declines more gradually because PPR keeps more receivers useful (1.0). QB, K and DST are cheap to stream, so a step there costs less (0.6 and 0.3).
- K and DST are always sorted below skill positions, whatever their score.
- Each row shows `#rank` and `scarcity +N` separately, so you can see *why* a player landed where they did.

It's a heuristic based on rank distance to replacement level, not true value-based drafting built on projected points, since no paid projection data was used.

### How the model evolved
1. **First version:** `replacement_rank − position_rank` alone. This answered the 2.10 question (it favoured the RB11 over the TE1), but it let scarcity *override* real differences in talent.
2. **K/DST bug:** late in the draft, a still-available top defense outscored deep bench RBs, which contradicted the strategy panel. The fix was to pin K and DST to the bottom.
3. **Blend fix:** an elite RB (ranked #3 overall) was scored below a WR ranked #12 overall. After the fix, consensus rank is the main signal and scarcity only adds a 0.4-weighted nudge.
4. **Slope fix:** because WR's replacement cutoff was deeper (40 vs 34), every WR got about 6 more scarcity points than an RB at the same depth. That flipped **13 adjacent RB-over-WR pairs**, all in the same direction. Per-position slopes removed every flip where the consensus gap was more than 5 spots. Six near-ties (gaps of 0.2–0.6 points) remain as genuine close calls.

## Bugs Found and Fixed

| Bug | Cause | Fix |
|---|---|---|
| "My Team" empty in mock drafts | Sleeper leaves `roster_id` null on mock-draft picks | Identify your picks by `draft_slot`, which is set in both mock and real drafts |
| Refresh reset the draft board | Draft ID was only kept in memory | Save the draft ID and slot to `localStorage` |
| VALUE/REACH labels reversed | `rank − pick_no` operands were the wrong way round | Changed to `pick_no − rank` |
| Taking Brian Robinson would also mark Bijan Robinson as taken | Name matching shortened first names to an initial ("b robinson") | Match on full normalized names |
| Drafted defenses never left Best Available | Sleeper labels them `DEF`, the rankings use `DST` | Normalize position labels |
| Wrong injury and experience data (e.g. Travis Etienne shown on IR; Jayden Daniels shown as a rookie) | The same initial-only matching in the offline data-enrichment script let Trevor Etienne and Jalon Daniels overwrite them | Fixed the script and re-checked all 160 players against Sleeper's data |
| Kenny Gainwell never matched as drafted | ESPN called him "Kenneth", Sleeper uses "Kenny" | Renamed him to match Sleeper |
| Wrong "rookie" / "sophomore" notes | Hand-written notes weren't checked against Sleeper's `years_exp` | Corrected 23 notes (12 second-year players, 7 third-year players, and others) |

All of the fixes were verified against a Sleeper **instant mock draft**, which works with the app exactly like a real draft.

## Lessons

- **Check for an API before building scraping or screenshot reading.** Sleeper's public API turned the "hard" idea into the easy one.
- **Test on a mock draft before relying on the app live.** Mock drafts showed up the `roster_id` difference and most of the other bugs before they could matter.
- **Name matching is the weakest point when joining datasets.** Shortening names to initials caused three separate bugs. Match on full names and check every player afterwards.
- **Fix a bug everywhere its logic is copied.** The matching bug was fixed in the app but left in the offline script, and it came back as wrong injury and experience data.
- **Keep heuristics secondary to consensus.** A scarcity score that overrides talent gives confident but wrong answers. Using it only as a nudge, and showing it separately, keeps the reasoning visible.
- **Expert rank vs ADP gaps are signals, not errors.** When a player's expert rank is far above their ADP, check for a recent trade or role change before treating it as a mistake.
