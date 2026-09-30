# Breakaway PRD Review Notes

Review of [[Breakaway_PRD_v3.0]] (raw source, draft v3.0 from March 2026), carried out on 2026-09-29 when it was converted from Word to Markdown. The PRD is a historical plan: its example race date (2026-04-26) has passed.

## Changes made during conversion
- **Personal data replaced with illustrative values:** FTP (now 250W), available training days (now Tue/Thu/Sat/Sun) and injury notes (now "None reported"). Sample readiness, HRV, CTL/ATL and memory-digest figures are example values only.
- **Formatting:** Word tables rebuilt as Markdown tables, highlighted boxes turned into callouts, and the prompt examples put in code blocks.

## Open issues in the PRD
1. **Strava API risk is understated (§9.3, §12.1).** Strava's November 2024 API agreement update restricts third-party use of Strava data in AI models, and limits showing a user's data to anyone except that user. Breakaway sends Strava-derived ride data to Claude, and Strava is its primary Phase 1 data source. Check the current Strava API terms before building on it. A direct Garmin integration or file upload may be needed as the Phase 1 source.
2. **Token numbers disagree.** The daily prompt is ~350–450 tokens in §7.3 and ~580 in §10.3. The memory digest is "under 200" tokens in §7.4 and ~150 in §10.3.
3. **Periodization overlap (§5.2).** A recovery week "every 4th week" collides with week 4 being the first Build week. Say whether recovery replaces week 4 or shifts later phases.
4. **Onboarding duplicate (§4.1, Block 3).** "Do you have a Whoop?" is already answered by the platforms checklist (Q9). If it's dropped, the questionnaire is 13 questions, not 14.
5. **Race-week weekdays are off by one (§8.3).** The table puts Race −1 on a Sunday, but the example race date (2026-04-26) is itself a Sunday.
6. **Dated example.** Weeks-out, race-date and phase examples are built around a race on 2026-04-26.

