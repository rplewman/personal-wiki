# Plan: The GRKN – shared meal-planning app for two

App name **The GRKN** is used in the manifest, page titles, home-screen icon label ("GRKN"), invite emails and push notifications.

## Context
You and your partner get stuck deciding what to cook each week, struggle to find new recipes that are good and nutritious, and have no shared shopping list you can both tick off live in the store. A previous Firebase attempt failed because the two of you weren't seeing each other's changes reliably, so **dependable real-time sync is the top requirement**. The finished app is:
- hosted online
- installable on both phones
- a week calendar for breakfast (optional), lunch and dinner
- a meal-prep guide for the start of the week
- a recipe library
- Claude-generated recipes (gluten-free by default, with a way to turn that off)
- recipe import from websites, Instagram and cookbook photos
- week suggestions that share ingredients, so you shop smarter
- step-by-step cook cards with timers
- a simple UI where the **ingredient list gets top priority**

The folder `C:\Users\thoma\GRKN` is empty, so this is a new build.

## Decisions (confirmed)
- **Backend and sync: Convex.** Every query updates live on both phones, writes show on screen immediately and then sync, changes are transactional, and it reconnects and resends on its own. It also stores files (recipe photos) and runs the server functions that call Claude, so the Anthropic key never reaches the phone.
- **Frontend: a web app built only for iPhone** (you both use iPhones). It uses Next.js (App Router) + TypeScript + Tailwind + shadcn/ui, is installed to the home screen from Safari, and is hosted on Vercel. There is **no desktop layout**. On a computer it shows as a centred, phone-width screen.

## iPhone-first UI rules (built in from day one, never added later)
- **Screen fit:**
  - It opens full screen from the home screen, using the standard iOS home-screen app settings (status bar style, app icon, launch screens).
  - Content avoids the notch and home bar (`viewport-fit=cover`).
  - Layout uses the dynamic viewport height, so the Safari toolbar never cuts off content.
  - Background bounce is locked, so pull-to-refresh can't fight with scrolling.
- **Native patterns:**
  - a bottom tab bar that sits above the home indicator
  - bottom sheets (`vaul`) instead of pop-ups
  - swipe to delete and swipe between weeks and cook steps (`framer-motion`)
  - large titles and back navigation that feel like iOS
  - press states instead of hover effects
- **Touch:**
  - tap targets are at least 44pt
  - text fields use 16px text, so iOS doesn't zoom in
  - the number keypad appears for quantities
  - no action depends on hover or a right-click
  - long-press actions have a visible alternative (⋯ menu)
- **iOS limits planned around:**
  - Safari has no vibration support, so timers use sound plus push. The sound is unlocked when you tap Start, because iOS requires a tap before playing audio.
  - Keeping the screen awake needs iOS 18.4 or later in a home-screen app. It fails silently on older versions.
  - Push needs the app installed to the home screen (iOS 16.4+).
  - Web Share Target isn't supported on iOS, so Instagram and website sharing uses a **"Send to GRKN" iOS Shortcut** in the share sheet. The Shortcut opens `/create/import?url=…`. Setup is a one-tap install link from Settings. Pasting the link also works.
  - The camera for cookbook pages opens through a file input set to capture, and each photo is shrunk on the phone to about 1600px before upload (fewer tokens and faster).
- **Performance on a phone:**
  - lists load recipes on the server, only small interactive pieces run on the phone
  - no big libraries
  - fonts use the iPhone's own font, SF Pro (`system-ui`)
  - the app shell is saved on the phone, so it opens instantly
- **Login: Convex Auth** with an email magic link (sent through Resend) and Google. Each of you has your own account in one shared **household**, joined with a 6-character invite code.
- **Gluten (coeliac-strict):** a household setting, **"Gluten-free by default: ON"**. On the generate and plan screens there's a toggle, "Include gluten this time (e.g. she's away)". Each ingredient gets `glutenRisk: none | contains | check-label`:
  - **contains** covers wheat, barley, rye, malt, regular soy sauce, standard beer, and oats unless certified GF.
  - **check-label** covers stock cubes, sauces, spice mixes, sausages, chocolate and the like.
  - Every recipe gets a `glutenFree` flag, which is true only if nothing is marked `contains`.
  - The recipe page shows a banner listing items to check, and cross-contamination notes where they apply (separate toaster or colander, flour dust).
  - Imported recipes are checked by Claude and flagged, and a GF swap is suggested for each problem ingredient.
  - On the shopping list, `check-label` items carry a small "GF? check label" tag.
- **Recipe images: none.** Text-only cards with a clear layout (title, time, GF badge, key ingredients). Cookbook photos are kept only as the import source.
- **Store connectivity:** signal is fine, so standard Convex sync is enough (no offline outbox).

## Getting sync right (why this won't repeat the Firebase problem)
1. **Each shopping item is its own document.** When one person ticks "milk" and the other ticks "eggs", nothing conflicts.
2. **Ticks set a value; they don't flip it.** The tick action is `setChecked(itemId, checked: boolean)`, not "toggle". If you both tap the same item, the result is still correct and stable.
3. **Instant feedback:** every tick, add and reorder shows on screen immediately and then syncs.
4. **Server-side list building:** combining the week's recipes into a shopping list happens in one transactional step on the server. Rebuilding the list keeps ticked items, manual items and edits, and only adds, removes or adjusts the items that came from recipes.
5. **Connection indicator:** a small dot shows "Live / Reconnecting / Offline – changes will sync". Changes made while offline are held and sent when you reconnect.
6. **In the store:** the shopping screen keeps the phone awake, ticked items drop to the bottom of their aisle, and each tick shows who made it ("✓ by Rory").

## Data model (`convex/schema.ts`)
- `households` {name, glutenFreeDefault, region/country (for what's in season), units (metric), defaultServings}
- `members` {householdId, userId, displayName, glutenFree:boolean}; `invites` {householdId, code, expiresAt}
- `recipes` {householdId, title, description, servings, prepMin, cookMin, tags[], cuisine, source {kind: generated|url|instagram|photo|manual, url?}, glutenFree, glutenNotes?, **ingredients[]** {id, qty, unit, name, canonical, aisle, note?, optional?, glutenRisk, gfSwap?}, **steps[]** {id, text, timers[] {label, seconds}, ingredientIds[]}, nutritionPerServing {kcal, protein, carbs, fat, fibre}, favourite, cookedCount, lastCookedAt, notes (personal tweaks)}
- `ratings` {recipeId, userId, stars 1–5, wouldCookAgain, comment?, cookedAt}: one rating per person each time you cook it
- `tasteProfile` (one per member plus a household summary) {likes[], dislikes[] (ingredients or cuisines), spiceLevel, notes, summary}: the summary is rewritten by Claude from ratings, comments and dislikes every few ratings, and is included in every generation prompt
- `pantry` {householdId, name, canonical, qty?, unit?, useSoon:boolean, addedAt}: what's on hand. Items marked `useSoon` get priority when generating and planning. Ticking a shopping item can move it into the pantry (optional). "Mark recipe cooked" offers to remove the pantry items it used up.
- `pushSubscriptions` {userId, endpoint, keys, prefs {partnerChanges, sundayNudge, timers}}
- `mealPlan` {householdId, date (YYYY-MM-DD), slot: breakfast|lunch|dinner, recipeId? | freeText?, servings, addedBy, repeatGroupId?}, indexed by household+date. `repeatGroupId` links the same breakfast repeated across several days, so editing one of them can apply to all.
- Recipes also get `mealTypes[]` (breakfast|lunch|dinner|snack) and `makeAhead:boolean`, with fridge life in days.
- `households` also gets `slotsShown` {breakfast:boolean (default off, so breakfast appears only when you turn it on), lunch, dinner}, `prepDay` (default Sunday) and `targetsByMeal` {breakfast, lunch, dinner: {proteinG, fibreG}}.
- `shoppingItems` {householdId, name, canonical, qty, unit, aisle, checked, checkedBy?, checkedAt?, sources[] {recipeId, mealPlanId}, manual:boolean, sortKey}
- `staples` {householdId, canonical}: things you always have at home (oil, salt), left off generated lists
- `aiJobs` {householdId, kind, status, input, result?, error?}: Claude calls run in the background and the screen updates live when they finish
- `weeklyBriefs` {householdId, weekStart, proteins[] (e.g. salmon, chicken, tofu), theme? ("Mexican week"), notes?, targets {proteinG, fibreG} per serving, includeGluten, createdBy}: one brief per week, kept as history so each new week can be steered away from the last few
- `planDrafts` {householdId, weekStart, briefId?, status: drafting|accepted} + `planDraftSlots` {draftId, date, slot, state: pending|suggested|kept|empty, recipeId? | card?, freeText?, nutritionEst, updatedBy}: the shared Planning board. Each slot is its own document, so the two of you can edit different slots at the same time without clashing.
- `prepPlans` {householdId, weekStart, prepDay, basedOn (fingerprint of the kept meals), stale:boolean, sessions[] {when: "Sunday" | "Wednesday top-up", totalMin, tasks[] {id, text, durationMin, timers[], forMeals[] {date, slot, recipeId}, storage ("fridge, 4 days, airtight"), doneBy?, doneAt?}}, dontPrepAhead[] {item, reason}}: the week's meal-prep guide. Tasks are ticked off live by either of you.
- `seasonalProduce` {region, month, items[] {canonical, name, peak:boolean}}: a curated table of what's in season. It's generated once per region by Claude, can be checked and edited in Settings, and is then read for free (no AI call per request).

## Screens (4 tabs at the bottom, big tap targets)
1. **Week:** the calendar. A list of Monday to Sunday, each day with Breakfast (if turned on), Lunch and Dinner slots. Breakfast rows are compact, and one breakfast can be set to **repeat** ("Overnight oats Mon–Fri"), since breakfasts are usually the same for several days. At the top of the week is a **Meal prep card** (see below). Tap an empty slot to pick a saved recipe, generate one, or type free text ("leftovers", "eating out"). Swipe between weeks. At the top: **"Suggest my week"** and **"Build shopping list"**. Each week shows a chip like "12 shared ingredients".
2. **Recipes:** your library. Search, filter chips (Favourites, GF, Quick <30m, In season, Cuisine; "In season" shows recipes whose main vegetables are in season this month), and sort by "not cooked in a while". The recipe page shows **ingredients first**: a big tickable list with a servings scaler (± buttons) and gluten highlights. Below that come the steps, the "Add to week" button and **"Cook"**.
3. **Shop:** the shared list, grouped by aisle (Produce, Meat, Dairy, Pantry, Frozen, Other). Includes a quick-add box, each item's source recipe shown on long-press, and "Clear ticked".
4. **Create:** the Claude hub. At the top is an **"In season now"** strip: this month's vegetables and fruit as chips, with peak items starred. Tapping a chip opens Generate with that vegetable filled in. Below the strip are four cards:
   - **Weekly brief** (the main way to plan a week):
     - **Choose proteins:** tap-to-pick chips (salmon, chicken, beef mince, prawns, tofu, eggs, lamb, pork, white fish, lentils/beans, plus custom). A soft warning appears if you pick the same proteins as last week.
     - **Theme and notes (optional):** e.g. "something Thai" or "one fakeaway night".
     - **Slots:** which breakfasts, lunches and dinners to fill.
     - **Breakfast options** (when breakfast is included):
       - **Style:** quick (under 10 min), make-ahead (batch on prep day), or weekend brunch.
       - **Variety:** how many different breakfasts to have that week (for example, 1 on repeat for weekdays plus 1 weekend brunch).
       - **Gluten:** oats are only allowed if certified GF, and are flagged on the shopping list.
     - **Guidance (recommendations, not hard rules):** Claude aims for about 35 g protein and 10 g fibre per serving at lunch and dinner, and about 25 g protein and 8 g fibre at breakfast. You can change these for each meal type in Settings. Each meal shows its estimate with a soft indicator (green when near the target, amber when well below). Nothing is blocked or regenerated automatically.
     - **Gluten toggle.**
     - **What Claude returns:** a draft week built around the chosen proteins, with in-season vegetables in every meal and fibre from legumes, whole grains, veg and seeds. Ingredient overlap is kept high, and there's **variety versus the last 3 weeks**: different cuisines and cooking methods, and no repeated recipes.
   - **Planning board** (the iterative step between the brief and the calendar):
     - The draft week appears as a board of slot cards (day × lunch/dinner). New suggestions stream in slot by slot, so you can start reviewing before the whole week is done.
     - **Actions on each card:**
       - **✓ Keep:** locks the meal in.
       - **✎ Edit:** either tweak it in plain words ("less spicy", "swap salmon for prawns", "make it 20 min"), which Claude revises for that one recipe, or edit the ingredients and steps by hand.
       - **↻ Replace with a generated recipe:** optionally add a hint ("something with lentils").
       - **⇄ Replace with your own recipe:** pick from the library, or import one on the spot (paste a link, Instagram post or cookbook photo) or type it in. It goes straight into that slot.
       - **✕ Remove:** leaves the slot empty or sets free text such as "eating out".
     - **Regenerate the rest:** replaces every meal that isn't kept, taking into account the meals you've kept (for overlap, protein variety and not repeating cuisines).
     - **Week summary:** running protein and fibre averages, the proteins used, the number of shared ingredients, and the gluten status, all updating as you edit.
     - **Shared draft:** the draft is saved in Convex, so you both see and edit the same board live and can plan together from separate phones.
     - **Accept week:** writes the kept and filled slots to the calendar. You can then build the shopping list straight away.
   - **Generate:** ingredients to use, a "What's in season" toggle (based on region and month), cuisine or mood, max time, servings, and the gluten toggle. Returns **3 recipe cards** to save or add straight to a day.
   - **Import:** paste a website link, paste an Instagram link or caption, or take/upload photos of cookbook pages (several pages allowed). The result opens as an **editable draft** to check before saving.
   - **Plan smart:** pick which slots to fill and a mix (for example, 3 saved favourites and 2 new). Claude suggests a week that maximises ingredient overlap, showing a list of the shared ingredients, and the result can be accepted into the calendar in one tap. Weekly brief uses this same planner with extra inputs, and both lead to the same Planning board.
- **Pantry** (a section at the top of the Create tab, and also reached from Settings): a quick-add list of what's on hand, with a "Use soon" star. The Generate screen has a "Use my pantry" option.
- **Settings:** household and invite code, the gluten default, region and units, staples, your taste profile (editable likes and dislikes, plus Claude's summary), notification switches, **Export all recipes (JSON)**, and the Claude monthly spend cap.
- **Undo:** ticking, removing or clearing shows a 5-second "Undo" message.
- **Meal prep card** (at the top of the Week screen, built from the meals you've locked in):
  - **When it appears:** after "Accept week", or on request with "Make prep plan" once some meals are kept. Its summary line reads like "Sunday prep · ~75 min · covers 9 meals".
  - **Prep sessions:** each session is a checklist that either of you can tick off live. Tasks come in a sensible order, so oven and stovetop jobs run side by side. For example:
    1. Put the oven on and roast veg for Mon–Wed.
    2. While that's in, cook rice for 3 lunches and make the tahini sauce.
    3. Marinate the chicken for Tuesday.
  - **For each task:** how long it takes, which meals it's for, tap-to-start timers (the same ones as Cook mode), and how to store it (fridge or freezer, number of days, container).
  - **Food safety and freshness:** a "Don't prep ahead" list covers things like fish (cook on the day or 1 day ahead at most), cut avocado, and dressed salads. Anything that won't last until the day it's eaten is scheduled for a **midweek top-up** session instead.
  - **Gluten:** in weeks that include gluten, GF items are prepped first, with separate boards and colanders, and each container is labelled "GF" or "contains gluten".
  - **Breakfast:** make-ahead breakfasts (overnight oats, egg muffins, chia pots) are included in the prep session.
  - **Staying up to date:** if meals in the week change after the plan was made, the card shows "Meals changed – update prep plan".
  - **In Cook mode:** steps already done during prep show as "✓ Prepped Sunday" and are collapsed, so on the night you only see the remaining steps.
- **Cook mode** (full screen):
  - one step card at a time; swipe or tap to move on
  - timers found in the step text ("simmer 10 min") become tap-to-start timer chips
  - several timers can run at once in a strip at the bottom, with a sound and a push notification when each finishes
  - the screen stays awake
  - an "Ingredients" drawer is always one tap away and highlights what this step uses
  - "Done cooking" updates cookedCount and lastCookedAt and asks each of you for a quick rating: stars, would-cook-again, and an optional note. This feeds the taste memory.

## Cooking nights + calendar feed (build step 8.5, after the meal prep guide)
**Data model**
- `mealPlan` gets `cookMemberId?`: who is cooking that meal. Only dinners have a cook.
- `households` gets `defaultCooks` {monday…sunday: memberId?}, e.g. Rory cooks Mon and Wed. A new dinner takes the default cook for its day, and each dinner can be changed.
- `households` gets `dinnerTime` (default 19:00).
- `members` gets `calendarToken`: a secret random token for that person's calendar feed. It can be reset.

**Screens**
- **Week:** each dinner row shows the cook's initial ("R"). Tap it, or use ⋯ → "Who's cooking", to change the cook.
- **Settings → Cooking nights:** a chip per weekday to pick who cooks, and a dinner time.
- **Settings → Add to Google Calendar:** a "Subscribe" button, with steps to copy the feed link and add it in Google Calendar on the web (Other calendars → From URL). There's also a "Reset link" button.

**Calendar feed** (`convex/http.ts`, `GET /cal/<token>.ics`)
- It lists only the dinners where you're the cook, for the next 3 weeks. Free-text dinners ("eating out") are left out.
- Each event is called "You're cooking: Salmon traybake". It starts at dinner time minus (prep + cook) minutes and ends at dinner time. The description holds the prep and cook minutes, the gluten status and a link to the recipe.
- Once the meal prep guide (M8) exists, the feed also includes prep sessions for whoever is doing them, e.g. "Sunday prep · ~75 min · covers 9 meals".
- **Limits:** Google refreshes subscribed calendars only every few hours, up to about a day, so last-minute changes show up late. Google also ignores reminders set inside a feed, so you set a default notification for that calendar once in Google Calendar (e.g. 30 min before).
- **Instant option:** an "Add to Google Calendar" button on each planned dinner opens a prefilled Google Calendar event (a `calendar.google.com/…action=TEMPLATE` link). It's one tap and needs no sign-in.

**Verification:** Rory is set to cook Mon and Wed, so new dinners on those days get Rory. The feed contains only Rory's dinners, with the right start time and duration. Changing the cook moves the dinner between the two feeds. A reset link stops the old URL from working. Once M8 exists, prep sessions appear in the feed of the person doing them.

## Push notifications (`convex/push.ts`, with a `web-push` action and VAPID keys)
- These work on iPhone (iOS 16.4+) **only once the app is installed to the home screen**. Onboarding walks you through installing, then asks for permission.
- **Partner changes:** messages are grouped so there's no spam. For example, "Rory added 4 items to the list" or "Rory planned Thursday dinner" are sent after 2 minutes with no further changes, using a Convex scheduled function. You're never notified about your own changes.
- **Prep day reminder:** the morning of your prep day, e.g. "Sunday prep: ~75 min, 9 meals covered".
- **Sunday nudge:** a Convex cron job sends "Plan next week?" at a time you choose, only if next week has empty slots.
- **Cook timers while the phone is locked:** starting a timer also schedules a server-side push for when it finishes (`scheduler.runAt`), and cancelling the timer cancels it. The phone also plays a sound while the app is open.

## Claude integration (`convex/ai.ts`, a Node server function)
- Uses the `@anthropic-ai/sdk` with **structured output** (tool use / JSON schema matching `recipes`) so the results are always valid, typed recipes. **Load the `claude-api` skill before writing this file.**
- **Model choice by task, to keep costs down:**
  - `claude-haiku-4-5` for cheap, mechanical jobs: normalising JSON-LD imports, tagging aisles and gluten risk, and rewriting the taste summary
  - `claude-sonnet-5` for creative jobs: generating recipes, extracting recipes from photos or text, and the overlap planner
  - no Opus by default
- **The system prompt always includes:**
  - the gluten rule, which is coeliac-strict and requires Claude to set `glutenRisk` for every ingredient
  - the household taste profile summary and dislikes (hard exclusions)
  - the top-rated and low-rated recipe titles
  - the pantry's "use soon" items
  - region and current month (for seasonality)
  - units and servings
  - recently cooked titles, to avoid repeats
  - nutrition guidance: balanced plates and vegetables in every meal

  It also asks Claude to break timers down into seconds per step and to label each ingredient with its aisle and a canonical name.
- **Keeping prompts small:**
  - The system prompt, gluten rules and output schema are fixed text, placed first with `cache_control`, so repeat calls cost about 10% of the input tokens.
  - The changing parts (profile summary, pantry, recent titles) go after the cached block and are kept short: the profile is a summary of about 150 words or less, and recent titles are capped at 20.
  - The planner receives compact ingredient lists (canonical names only), not full recipes.
  - Each task sets a tight `max_tokens`.
  - Generating returns 3 short cards first (title, one-line description, key ingredients). The full recipe is generated only for the card you pick. That's about 3× fewer output tokens than generating three complete recipes.
  - Website imports that have JSON-LD skip Claude extraction entirely and only get a Haiku pass for tagging.
- **Spend guard:** each call logs its token usage to `aiJobs`. When the monthly cap (set in Settings) is reached, new calls are refused with a friendly message. Prompt caching is used on the long system prompt and profile.
- **Website import:** fetch the page on the server, then look for schema.org `Recipe` JSON-LD first, which is free and exact. Claude then only normalises it (aisles, canonical names, timers, GF check). If there's no JSON-LD, the cleaned page text goes to Claude to extract the recipe.
- **Instagram:** Instagram blocks scraping, so this takes two routes. First, try the public caption (og:description) from the link. If that fails, the screen asks you to paste the caption or add screenshots, which go to Claude vision. Links arrive through the "Send to GRKN" iOS Shortcut or by pasting.
- **Cookbook photos:** stored in Convex, then 1–4 page images are sent to Claude vision in a single request.
- **Overlap planner:** takes the saved recipes' canonical ingredient lists plus the constraints. Claude returns a week of existing recipe IDs and new generated recipes. The server then works out the actual overlap score itself rather than trusting the model's count.
- **Weekly brief planner** (`claude-sonnet-5`, one call per week):
  - **Inputs:** the brief (proteins, theme, targets), the in-season list for this region and month (from `seasonalProduce`), compact titles, cuisines and proteins from the last 3 weeks' plans (to avoid repeating them), saved recipe ingredient lists, and the pantry's "use soon" items.
  - **Output:** a structured result per slot (an existing recipe ID or a short new-recipe card), with a nutrition estimate per serving. Each slot is written to `planDrafts` as it arrives.
  - **Targets are soft:** they're passed to Claude as recommendations. The server only works out the estimates for the indicators and never forces a retry.
  - **Actions on a single slot:**
    - **Replace:** one small call, given the kept meals as context.
    - **Edit in words:** a Haiku call that revises that one recipe from your instruction.
    - **Regenerate the rest:** one call covering only the slots that aren't kept.
    - **Your own or imported recipe:** reuses the Import pipeline, and the result is saved straight into the slot.
  - **Full recipes on demand:** as with Generate, full recipes are written only for new cards you keep, which keeps output tokens low.
- **Prep planner** (`claude-sonnet-5`, one call per plan):
  - **Inputs:** only the kept meals, each sent in a compact form (recipe ID, date and slot, ingredients with amounts, step text, `makeAhead` and fridge-life days), plus the prep day and the gluten status.
  - **Output:** structured `prepPlans`, where each task names the meal slots and step IDs it covers.
  - **Server checks:** every task must point at real meals and steps. The server also recomputes each meal's "eaten on" day against the storage days Claude gives, and moves anything that would be too old into the midweek top-up.
  - **Updating:** "Update prep plan" regenerates the plan but keeps tasks you've already ticked.
- **Breakfast generation** uses the same Generate flow with a meal-type selector. Breakfast cards are kept short, and make-ahead breakfasts get `makeAhead` and fridge-life days.
- **Seasonal suggestions:** the "In season now" strip, the Generate toggle and the Recipes filter all read `seasonalProduce`, so they don't cost an AI call. The table is created with one Haiku call per region the first time, then reviewed in Settings.
- **Nutrition accuracy:** protein and fibre are estimates. The recipe page labels them "≈ estimated", and portion sizes of the protein are stated in grams so the numbers can be checked.

## Shopping list build (`convex/shopping.ts`)
Uses the week's plan entries × a scale factor (planned servings ÷ recipe servings) → combines ingredients by `canonical` → converts units where the family matches (g/kg, ml/l, tsp/tbsp/cup) and otherwise keeps separate lines → leaves out `staples` → matches the result against the existing items: sources get updated, ticked and manual items are kept, and items no longer needed from any recipe are removed. Kept as pure functions in `lib/ingredients.ts` so they can be unit tested.

## Project layout
```
GRKN/
  app/(tabs)/week, recipes, recipes/[id], recipes/[id]/cook, shop, create/{generate,import,plan}
  app/join/[code], app/settings, app/manifest.ts
  components/ (RecipeCard, IngredientList, StepCard, TimerStrip, WeekGrid, ShopItem, SyncDot)
  convex/ schema.ts, auth.ts, households.ts, recipes.ts, mealPlan.ts, shopping.ts, ai.ts, import.ts
  lib/ ingredients.ts (units, merge), timers.ts, week.ts
```

## Build order
1. Set up the project: Next.js, Tailwind, shadcn, Convex, Convex Auth (magic link + Google), households and invite codes, the installable-app manifest and icons, a Vercel project, and `ANTHROPIC_API_KEY` and `AUTH_RESEND_KEY` stored in Convex env.
2. **Shopping list first**: tick, add and clear with instant updates, the connection dot, and the screen-awake lock. Then test it on two phones before building anything else, to prove the sync works.
2.5. Shopping bundles: one-tap saved item groups (see PROGRESS.md for the agreed design).
3. Recipe library: manual entry, the recipe page with ingredients first, and the servings scaler.
4. Week calendar with breakfast (optional, repeatable), lunch and dinner, plus "Build shopping list" (list combining + tests). Breakfast is part of the data model from here onwards.
5. Cook mode with timers, ratings and notes.
6. Claude, part 1: the seasonal produce table and "In season now" strip, generate (with the coeliac rules, taste profile and in-season toggle), then import (URL → Instagram → photos).
7. Claude, part 2: the overlap planner, **Weekly brief** (proteins, soft protein and fibre targets, variety across weeks) and the shared **Planning board** (keep, edit, replace with a generated or your own recipe, remove, regenerate the rest), plus pantry and "use soon" and the taste-profile summary rewrite.
8. **Meal prep guide:** the prep planner, the Meal prep card with live-ticked tasks and timers, the "Don't prep ahead" list and midweek top-up, the "Meals changed" prompt, and "✓ Prepped" steps in Cook mode.
8.5. Cooking nights (who cooks each dinner, default cook per weekday) + a Google Calendar feed with cook and prep times, and prep sessions from M8.
9. Push notifications: install onboarding, partner-change messages, the Sunday cron job (which opens the Weekly brief), the prep day reminder, locked-screen timers.
10. Polish: the Recipes "In season" filter, staples, "not cooked lately", nutrition display, export, undo, and the spend cap.
11. **Tentative – native iOS wrapper with alarm timers** (see below). Could replace or sit next to 9; decide after 8.

## Native iOS wrapper (tentative, not committed)
- **Why:** a home-screen web app can't sound on a locked phone or through the silent switch (found in M5). Push (9) helps, but it's a normal notification sound that silent mode and Focus still mute. Only a native app can set real timers.
- **What:** wrap the existing app with **Capacitor** (same Next.js code, Convex and sign-in inside a native iOS shell; no rewrite). Add a small Swift plugin for **AlarmKit** (iOS 26+): Cook-mode and prep timer chips start real system timers that ring like the Clock app (lock screen, silent mode, Focus), with a Live Activity countdown on the lock screen and in the Dynamic Island. They run on the phone, so no signal is needed. In the plain web version the chips keep working as they do now.
- **Nice extras once native:** push without "Add to Home Screen", a real share-sheet target instead of the "Send to GRKN" Shortcut, simpler camera import.
- **Building without a Mac:** all code is written on Windows; the iOS build runs in the cloud on **Codemagic** (free monthly Mac build time, automatic code signing, uploads to TestFlight). GitHub Actions Mac runners are the fallback. No simulator on Windows, so each native change is tested on the phone via TestFlight (~15–30 min per round); keep the native part small. A Mac mini isn't planned for now.
- **Distribution:** TestFlight internal testing for the two of us (no App Store review, no public listing).
- **Needs:** Apple Developer account ($99/year), a Codemagic account linked to the GitHub repo, an App Store Connect API key for signing/upload, app icons and launch screen.
- **Work:** about one milestone (wrapper, AlarmKit plugin, TestFlight pipeline), plus one-off Apple setup.

## Keeping the build efficient (Claude Code token use)
- **Generate code with tools:** use official generators (`create-next-app`, `npx convex dev`, `shadcn add`, `@convex-dev/auth` init) instead of writing boilerplate by hand.
- **No subagents,** and only one browser check per milestone. Read screen state as text rather than screenshots, unless it's a visual check.
- **Write each file once.** Make targeted edits after that, don't reread files that were just written, and keep shell output short with `--silent` or `tail` on installs and builds.
- **Reuse over custom:** shadcn components for the UI, Convex's own optimistic-update helpers, the `web-push` library, and schema.org parsing with a small hand-written extractor (no heavy scraping libraries).
- **Small milestones:** each build step ends with a quick check (typecheck + relevant tests), so errors are caught early rather than debugged across the whole app.
- **Short commit messages** and no long explanations between steps. I'll report in at the end of each milestone.

## Later (not in v1)
Leftovers and batch cooking (one cook fills two slots), aisle order per store, a durable offline outbox, and AI images.

## Accounts / keys you'll need
Convex (free), Vercel (free), Anthropic API key, Resend (free, for magic links), Google OAuth client (optional). I'll generate the VAPID keys for push notifications. Your region is needed for "in season"; it gets set in Settings.

## Verification
- **Unit tests (Vitest):** `lib/ingredients.ts` combining and unit conversion; timer detection from step text; the rule that `glutenFree` is derived from `glutenRisk`.
- **Gluten checks:** a fixed set of 10 prompts and imports (including soy sauce, stock, oats and beer batter) must come back with the correct `glutenRisk` flags. This set is re-run whenever the prompts change.
- **Weekly brief checks:** a brief of salmon + chicken uses both, puts an in-season vegetable in every dinner, and shares no recipe titles with the previous week's plan. The protein and fibre indicators show and update correctly.
- **Breakfast checks:** turning breakfast on and off shows and hides the rows. A breakfast repeated Mon–Fri adds the right total amounts to the shopping list (5 servings), and editing it changes all the linked days.
- **Prep plan checks:** a week with salmon on Thursday must not prep the salmon on Sunday. Every task links to a meal that's actually kept. Changing a kept meal marks the plan "Meals changed". Ticking a task on one phone shows on the other within about 1 second.
- **Planning board checks:** keep 2 meals then "Regenerate the rest", and the kept meals stay unchanged. Edit a meal in words and only that slot changes. Replace a meal with a library recipe and with an imported link. With two sessions open on the same draft, each person's edits to different slots appear for the other within about 1 second.
- **Push notifications:** both installed iPhones receive a partner-change message and a locked-screen timer alert.
- **Real-phone check after milestone 2:** install on both iPhones from the Vercel URL, and confirm the shopping list syncs and feels native before any more features are built.
- **Convex function tests (`convex-test`):** rebuilding the list keeps checked and manual items; both of you calling `setChecked` at the same time ends up correct; household access rules (one household can't read another's data).
- **iPhone layout test (Playwright WebKit with the iPhone 15/SE device profiles):** no sideways scrolling, the tab bar clears the home indicator, tap targets are at least 44px, and text fields are at least 16px. This runs on every milestone.
- **Two-person sync test (Playwright):** two browser sessions logged in as different members. A ticks, B sees it within about 1s. Both tick different items at the same time. B goes offline, ticks, comes back, and A receives it.
- **Manual checks:** install the app on both phones from the Vercel URL, then do a real shop together; generate a GF recipe and a non-GF one; import one website, one Instagram post and one cookbook photo; run cook mode with 2 timers at once.
