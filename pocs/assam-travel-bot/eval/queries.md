# Eval queries

Expected route: `KB` (knowledge base) · `WX` (weather) · `EXP` (expert escalation) · `KB+WX` (compound) · `REFUSE/CLARIFY` (correctly declines or asks a follow-up instead of guessing).

## Pure place-info (KB)

1. **"What's Jatinga near Haflong known for, and is it worth a detour?"**
   Good answer: describes the place's known draw, notes how to reach it from Haflong, cites the KB entry. Doesn't overclaim specifics it isn't sourced on.
2. **"Tell me about Dehing Patkai — what makes it different from Kaziranga?"**
   Good answer: comparative, grounded in KB entries for both, doesn't invent a comparison point neither entry supports.
3. **"Any lesser-known heritage sites near Sivasagar besides the usual ones?"**
   Good answer: uses metadata filter (district=Sivasagar, category=heritage), lists 2-3 KB entries with brief distinguishing detail each.
4. **"Where can I see gibbons in Assam without going to a big national park?"**
   Good answer: surfaces the relevant sanctuary from KB, notes access/best time if present in the entry.
5. **"What's Sualkuchi and why do people go there?"**
   Good answer: KB-grounded description (craft/weaving village), practical visiting note.
6. **"Is there anywhere good for river islands other than Majuli?"**
   Good answer: tests whether it over-indexes on the famous example (Majuli) instead of surfacing the actually-underrated KB entries the bot is meant to specialize in.
7. **"What's the significance of Batadrava for someone interested in Assamese culture?"**
   Good answer: grounded cultural/historical note from KB, not generic filler.
8. **"Give me 3 offbeat wildlife spots in Upper Assam."**
   Good answer: metadata filter (region=Upper Assam, category=wildlife), returns a short list, each with a one-line hook — tests multi-result synthesis, not just single-place lookup.

## Pure weather (WX)

9. **"What's the weather like in Haflong right now?"**
   Good answer: live current conditions, phrased so it's clearly sourced from the weather API, not "generally Haflong has a pleasant climate" vagueness.
10. **"Will it rain in Dehing Patkai this weekend?"**
    Good answer: forecast-based, explicit about the forecast's time window and uncertainty — not stated as certain fact.
11. **"Is it monsoon season in Jatinga right now?"** *(seasonal framing, not a spot forecast)*
    Good answer: correctly distinguishes "what season is it" (roughly known/calendar-based) from live conditions; doesn't need the weather API to hallucinate false precision.
12. **"What's the best month to visit Kaziranga's outskirts for weather, not crowds?"**
    Good answer: this is a seasonal-pattern question, not a live-forecast one — tests whether the router sends it to KB (if the KB has a best-season field) rather than forcing a weather-API call for a question the API can't actually answer.
13. **"Should I carry a rain jacket to Manas this week?"**
    Good answer: derives a practical recommendation from the live forecast, doesn't just dump raw numbers.
14. **"What's the temperature difference between Guwahati and Haflong today?"**
    Good answer: two weather-API calls, compared — tests whether the pipeline handles a compound weather query, not just single-location.

## Itinerary / compound (KB+WX)

15. **"I have 3 days — plan a trip covering one wildlife spot and one heritage site, avoiding the rainiest days."**
    Good answer: combines KB picks with a weather-informed day ordering. The hardest single query in the set — a weak answer here (e.g., ignoring weather entirely, or listing places with no logistics) is a meaningful signal.
16. **"Is now a good time to visit Nameri, weather-wise, and what would I actually do there?"**
    Good answer: WX for timing + KB for activity description, one coherent answer, not two disconnected paragraphs.
17. **"Plan a 2-day heritage trip near Sivasagar and tell me what to wear."**
    Good answer: KB for the sites, WX for the clothing recommendation.
18. **"Compare Jatinga and Haflong for a weekend trip, weather included."**
    Good answer: tests balanced compound synthesis across two places at once.
19. **"What's a good offbeat add-on near Kaziranga if the weather's bad for the main park?"**
    Good answer: conditional logic — the answer should actually depend on what the weather call returns, not be canned.

## Expert escalation (EXP)

20. **"Can someone local show me around Dehing Patkai — is that something you can arrange?"**
    Good answer: explicit ask for a human — should escalate immediately, not attempt a KB answer first.
21. **"Is the road to [an obscure KB-listed village] currently passable? I heard it washes out sometimes."**
    Good answer: current/hyperlocal road-condition question the KB and weather API can't answer — should escalate rather than guess.
22. **"I want to do a homestay with a local family near Majuli, not a hotel — who do I talk to?"**
    Good answer: booking/logistics beyond KB scope — escalate.
23. **"What's a place near Haflong that's not written up anywhere online?"**
    Good answer: explicitly asking for something outside any documented source — correct behavior is to say the KB doesn't have this and offer expert escalation, not to fabricate a hidden gem.
24. **"Is it safe for a solo woman traveler to visit [remote KB-listed spot] right now?"**
    Good answer: safety-critical + current + hyperlocal — should escalate rather than let the LLM assert a safety judgment from general knowledge. This is a guardrail check, not just a routing check.

## Edge cases

25. **"What about Ziro Valley?"** *(a real place, but in Arunachal Pradesh, not Assam)*
    Good answer: correctly recognizes it's out of the bot's stated scope (Assam) and says so, rather than answering as if it were in-KB or silently treating it as Assam.
26. **"Tell me about [a plausible-sounding but nonexistent place name]."**
    Good answer: KB retrieval finds nothing relevant; the bot says so and offers to help differently (nearby real suggestion, or expert), rather than inventing a description. This is the single most important hallucination check in the set.
27. **"What's your favorite place in Assam?"**
    Good answer: light out-of-scope/chitchat handling — brief, doesn't break character or refuse oddly, doesn't overclaim a "favorite."
28. Multi-turn: **Turn 1:** "Tell me about Jatinga." → **Turn 2:** "What's the weather like there this week?"
    Good answer: turn 2 correctly resolves "there" to Jatinga from session context and routes to WX — tests entity carry-over across turns, not just single-shot routing.
29. Multi-turn: **Turn 1:** "Suggest a quiet nature spot." → **Turn 2:** "Somewhere else, that one's too far from Guwahati."
    Good answer: treats turn 2 as a refinement (distance constraint) on the same intent, not a fresh unrelated query.
30. **"I'm planning a trip in monsoon — is that a bad idea overall for the underrated spots you know about?"**
    Good answer: a broad, KB-spanning seasonal question — tests whether the bot can generalize across multiple entries' season fields into one coherent answer instead of only handling single-place questions.
