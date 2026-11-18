# Dashboard Design: Analytical Questions, Charts and Interactions

Phase 3 design document. It fixes **what the dashboard must answer** and **why each chart is the right form for that question**, before any code is written. Chart types follow from the questions and from the shape of the data, never the other way round. Chart forms are named and checked against the **Financial Times *Visual Vocabulary*** (https://ft-interactive.github.io/visual-vocabulary/). Seven of its 9 categories are used (§3a).

**Status:** approved 2026-11-12; simplified 2026-11-13 (§9); restructured 2026-11-17 around a few analytical questions (§10); host advantage became its own question and the tabs moved to an animated icon rail (§11); the Overview became visuals only (§12); **the icons and the Filters button float at the top, and tab captions were cut to the essential notes** (§13). Five questions: one per analytical tab, two on Countries & Medals. The Overview tab is descriptive and has no question. Charts carry plain descriptive titles: each is evidence for its tab's question. §8 and §9 are kept as a record and use earlier numberings.

---

## 1. Purpose and users

**Purpose:** let a user explore 126 years of Olympic history from four perspectives (countries, bodies, gender, sports) and compare across time, place and discipline.

**Typical user:** a student, analyst or sports fan who has a question ("Did host countries really win more?", "Are rowers getting taller?") and wants to filter, compare and drill down rather than read a fixed report.

**Guiding principle:** overview first, then filter and zoom, then details on demand. Every tab opens on a meaningful default view. Filters narrow it, selections link the charts, and hover or a table gives the exact numbers.

---

## 2. The analytical questions

The dashboard is designed to investigate **five questions**: one per analytical tab, and a second one on the Countries tab. Each question is stated as a heading; every chart under it looks at one aspect of it. The Overview tab is not a question: it shows what is in the data (headline numbers, the structure of the programme, an athlete search).

| # | Tab | Question | Aspects, and the chart that shows each |
|---|---|---|---|
| **Q1** | Countries & Medals | **What drives a country's Olympic success: size, wealth or specialisation?** | *who wins*: medal map · *size and wealth*: medals vs GDP and population · *specialisation*: medals by country and sport |
| **Q2** | Countries & Medals (second heading) | **Do hosts win more at home?** | hosts at home vs their usual share (dumbbell) |
| **Q3** | Physiques | **How do athletes' bodies differ between sports, how have they changed, and do medallists stand out?** | *change*: focus sport over the decades · *difference between sports*: focus sport among all Olympians (height × weight) · *medallists*: medallists vs the rest of the field |
| **Q4** | Gender | **How did women gain their place at the Games, over time, across sports and across countries?** | *over time*: share of women at each Games · *across sports*: when each sport opened to women · *across countries*: women and men per team |
| **Q5** | Sport Comparison | **Which sports select for similar athletes?** | *overall similarity*: sport similarity map · *how different in detail*: the chosen sports side by side |

### What the data shows (checked against the data; used in the demo)
* **Q1:** wealth explains much of the medal table but not all of it: at Tokyo 2020 Jamaica won 4.8× the medals its GDP predicts. Countries specialise strongly: Norway wins 8× its usual share in cross-country skiing; Russia (with the USSR) 2.5× in artistic gymnastics.
* **Q2:** yes, almost always: hosts did better at home in 28 of 29 Summer Games, typically 1.7× their usual share of medals.
* **Q3:** sports select for very different bodies, and the gap has grown: male rowers' median height rose from 180 cm (1948) to 192 cm (2020), much faster than the all-sports line. Medallists can differ from the field: male swimming medallists are 4 cm taller (187 vs 183 cm).
* **Q4:** women went from 1.8 % of athletes (1900) to 11 % (1960) and 48 % (2020). Sports opened at very different times (athletics 1928, football 1996, wrestling 2004, boxing 2012), and Nordic combined is still men only. China is the only large team with more women than men over its history (55 %).
* **Q5:** two axes capture 75 % of the differences between sports (body size, then age). Sports form families: basketball sits with water polo, baseball and rugby; gymnastics and artistic swimming sit at the opposite end.

## 3. Charts, and why each form

Each table lists a tab's charts by their card title. Forms are chosen from the data's job (magnitude, distribution, relationship, geography, hierarchy, change). Not one of the main analytical charts is a plain bar, line or pie chart.

### Overview (descriptive)
| Card | Chart | Why this form | Data |
|---|---|---|---|
| Sports and events by number of athletes | **Treemap** (full width): Season → Sport → Event, sized by number of athlete entries; click a sport to zoom into its events. Each sport sits under its own season: figure skating (1908, 1920) and ice hockey (1920) were held at Summer Games before the Winter Games began, but are shown under Winter, with the early entries noted on hover | The programme is a strict hierarchy. FT recommends the treemap for hierarchical part-to-whole (and advises against the sunburst), and rectangles make sizes easier to compare | athlete_events |
| Athlete search | **Searchable athlete table** (name search, sortable, paged) plus an **athlete card** on row click: bio, every Games, events, medals | Searching for a named individual is a lookup task, which a table does best | athlete_games, athlete_events |

### Countries & Medals (Q1, Q2)
| Card | Chart | Why this form | Data |
|---|---|---|---|
| Medals by country | **World map, two encodings by metric**: medal **totals → proportional-symbol map** (circle size = medals); **rates** (per million people / per $100bn GDP) **→ choropleth**. Default: totals over the filter's year range; a toggle switches to one Games at a time with a slider and ▶ play control. Historic teams keep their own circle (D15) | Geography is the point of the question. FT rule: choropleths show rates, totals belong on proportional symbols (shading big countries by raw totals exaggerates them by land area) | country_games |
| Size and wealth | **Bubble scatter**: x = GDP (log), y = medals (log), size = population, one bubble per country for the chosen Games; dashed trend line | Relationship between two continuous variables over orders of magnitude needs a log-log scatter. Distance from the trend line *is* over/under-performance | country_games (1960+) |
| Hosts at home vs their usual share (Q2) | **Dumbbell**: each host nation's medal share at its home Games vs its average share in the neighbouring Games (±2), with a one-line summary | Before → after comparison per item is the canonical dumbbell job | country_games.is_host |
| Specialisation | **Heatmap**: countries (rows) × sports (columns). Toggle: medal count ↔ **specialisation index** (country's share of medals in a sport ÷ its share of all medals; >1 = specialised). **Historic teams are combined with their successor** (USSR, Unified Team, ROC → Russia; East/West Germany, Saar → Germany; …), marked * | Two categorical dimensions with a magnitude per cell. The index removes the "big countries win everything" effect. A specialisation is a long-run trait of a sporting nation, so splitting it across flags would hide it | medals_by_sport + `da.lineage()` |

### Physiques (Q3)
One measure switch (Height / Weight / BMI / Age) and one **focus sport** menu drive all three charts.

| Card | Chart | Why this form | Data |
|---|---|---|---|
| Focus sport over the decades | **Trend with uncertainty band** (full width): median (line) and interquartile range (band) per Games for the focus sport, women and men; dashed = all sports of the same season; sample size *n* on hover | Change over time with spread. The band shows whether shifts exceed the normal variation; *n* exposes thin early data (D11) | athlete_games |
| Focus sport among all Olympians | **2D density contour** of height × weight for all athletes (gray), with the focus sport's athletes overlaid as points | 100k+ points overplot; a density shows where athletes concentrate, and the overlay places one sport inside the whole | athlete_games |
| Medallists vs the rest | **Split violin**: medallists vs non-medallists in the focus sport | Two distributions compared head-to-head; a split violin puts them back-to-back on one axis | athlete_games |

### Gender (Q4)
| Card | Chart | Why this form | Data |
|---|---|---|---|
| Over time | **Line of women's share (%)** per Games, Summer and Winter, with **annotated milestones** and a 50 % parity reference line; a followed sport is added as a dotted line | One measure over time; annotations turn it into an explanation | participation |
| Across sports | **Priestley timeline**: one row per sport still on the programme, from its first to its latest Games; gray = men only, violet = women also compete; a dot marks the first Games with women; the share of women at the latest Games is written at the end of the row ("men only" / "women only" in words) | The question is *when* something started and how long it has lasted, which is what a timeline of bars shows. Writing the current share as text avoids the problem of the former sport × decade heatmap, where all-men and all-women decades were solid colour blocks that said little | athlete_games |
| Across countries | **Spine chart per country**: each delegation as one bar split into women (left, violet) and men (right, aqua) around a 50 % parity line; top 25 delegations, sorted by imbalance | FT *Deviation*: the spine chart is listed for exactly this "split one value into Male/Female" case. Distance from the centre line *is* the gender gap | athlete_games |

### Sport Comparison (Q5)
| Card | Chart | Why this form | Data |
|---|---|---|---|
| Sport similarity map | **Sport similarity map**: PCA of the standardised sport profiles (mean height, weight, BMI, age, % female). Each sport is a point sized by athlete count, shaped by season, gray unless selected; axis loadings shown | Many variables per item reduced to 2D so that *distance = similarity*. Clusters emerge visually (power sports, endurance, small-and-light, tall team sports) | sport_profiles (recomputed for the filter) |
| The chosen sports side by side | **Overlaid distributions** (small multiples: height, weight, age): one translucent violin per selected sport, median marked | Averages hide the overlap. The distributions show how distinct the sports really are | athlete_games |

**Chart-type inventory:** treemap, table, proportional-symbol map, choropleth, bubble scatter (log-log), heatmap, dumbbell, trend band (fan), 2D density, split violin, annotated line, Priestley timeline, spine chart, PCA scatter, overlaid violins. That is 15 forms: 13 serve the five analytical questions, 2 describe the data (Overview).


### 3a. Coverage of the FT Visual Vocabulary

The FT chart names are in *italics*.

| FT category | FT definition (short) | Our chart(s) | Tab question |
|---|---|---|---|
| **Deviation** | variation (+/−) from a reference point | *spine chart*: women vs men around 50 % parity; diverging specialisation index | Q4, Q1 |
| **Correlation** | relationship between two or more variables | *bubble*: medals vs GDP vs population; *XY-heatmap*: country × sport; *scatterplot*: PCA similarity map; height × weight density | Q1, Q5, Q3 |
| **Change v Time** | changing trends | *line* with annotations; *fan*: median + IQR band over time; *Priestley timeline* | Q4, Q3 |
| **Distribution** | values and how often they occur | *violin* (split and overlaid), *dot-plot* (dumbbell) | Q3, Q5, Q2 |
| **Part to whole** | an entity broken into components | *treemap* (Season → Sport → Event) | Overview |
| **Magnitude** | size comparisons | *proportional symbols* | Q1 |
| **Spatial** | geographical patterns | *proportional-symbol* map (totals); *basic choropleth* (rates) | Q1 |
| Ranking | position in an ordered list | not a chart of its own any more: only ordered rows (spine chart by imbalance, heatmap by medal total) | (Q4, Q1) |
| Flow | volumes moving between states | **not covered** since the Sankey was removed (2026-11-13) | — |

---

## 4. Interactions

### 4.1 Global filters (panel behind the Filters button)
The filters live in a panel that grows out of the **Filters** button (top right, always visible) and collapses back into it with ×. The charts update while it is open, and the filters stay applied when it is closed. A badge on the button counts the active filters, and the **Showing:** bar at the top of the page always lists them; each tab's exceptions are stated once, under its question.

| Control | Type | Default |
|---|---|---|
| Years | range slider, 1896–2022, marks at each Games | full range |
| Season | segmented: Both / Summer / Winter | Both |
| Sex | segmented: All / Women / Men | All |
| Sports | searchable multi-select + checkbox "Hide minor sports (< 100 athletes)" | all, minor hidden |
| Countries | searchable multi-select (country name or code) | none = all |
| Reset | button: back to defaults | |

**Which filter affects which tab:**

| Filter | Overview | Countries | Physiques | Gender | Sports |
|---|---|---|---|---|---|
| Years | ✔ | ✔ | ✔ | ✔ | ✔ (profiles recomputed) |
| Season | ✔ | ✔ | ✔ | ✔ | ✔ |
| Sex | ✔ | ✔ | ✔ | — (the tab compares sexes) | ✔ |
| Sports | ✔ | ✔ (heatmap, medals) | ✔ | ✔ | — (has its own sport picker) |
| Countries | ✔ | **highlight**, not filter | ✔ | ✔ | ✔ |

On the Countries tab, selected countries are *highlighted* rather than filtered out, so they can be compared against everyone else.

### 4.2 Linked views (selection in one chart updates others)
| Tab | Action | Effect |
|---|---|---|
| Overview | click a sport in the treemap | the athlete table lists that sport's most decorated athletes (search stays active) |
| Overview | click an athlete row | athlete card opens |
| Countries | click a country on the map, scatter or host chart | adds it to the selected countries; highlighted in all charts (selecting the USSR highlights Russia's combined row on the heatmap) |
| Countries | ▶ play | the map steps through the Games |
| Physiques | choose a focus sport | overlaid on the density plot; drives the trend and violin charts |
| Gender | click a sport on the timeline | the share line adds that sport's female-share trend; click again or Clear to stop |
| Sports | click or lasso sports on the similarity map | adds them to the comparison (max 4; oldest drops out); picker stays in sync |

### 4.3 Everywhere
* **Hover tooltips** with exact values and sample size *n*.
* **Zoom/pan** on all Cartesian charts (Plotly built-in), with double-click to reset. The map zooms with its toolbar buttons only, so the mouse wheel always scrolls the page.
* **Empty states:** "No athletes match these filters" instead of an empty or broken chart.
* **Data notes** under charts where needed: e.g. "GDP data from 1960 only", "Historic teams (USSR, GDR …) are not in World Bank data", "n = 412 athletes with known height".

---

## 5. Layout

```
   Olympic Athletes Explorer                  ╭ ◎  🏅  🏃  ⚥  🏀 ╮  ╭ ⏷ Filters ² ╮
   (title scrolls away)                       ╰────────────────╯  ╰──────────────╯
                                              icon bar (fixed)    fixed; the panel
                                                                  grows out of it
   Showing: 1896–2022 · Summer and Winter · Women and men
   [Q1] What drives a country's Olympic success: size, wealth or specialisation?
   ⓘ Countries chosen in the filters are highlighted here, not filtered out. …
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  main chart (full width)                                                  │
  └───────────────────────────────────────────────────────────────────────────┘
  ┌────────────────────────────────────┐ ┌────────────────────────────────────┐
  │  chart                             │ │  chart                             │
  └────────────────────────────────────┘ └────────────────────────────────────┘
   data note · source
```

* Each analytical question is a heading (Countries & Medals has two: Q1, and Q2 further down). A line under it appears only for a rule the reader must know (ⓘ): selected countries are highlighted, not filtered (Countries); the Sex filter does not apply (Gender); the Sports filter does not apply (Sports).
* The tabs are icons in a translucent bar floating at the top right, just left of (and separate from) the Filters button (Olympic rings, medal, runner, ♀♂, ball); the name appears under an icon on hover and a highlight slides to the active one. On phones the bar floats at the bottom. The title scrolls away with the page.
* The **Filters** button floats at the top right in the same glass style. The filter panel grows out of it and collapses back into it; its controls use the same pill style (light-blue / white active pill).
* Each chart card carries a plain descriptive title, its chart type and FT category, and a one-line "how to read" hint.
* The footer on every tab cites the sources (Olympedia via Kaggle, World Bank).
* An **About** modal holds the data sources, licenses and a summary of the cleaning decisions.

---

## 6. Visual design system

**Theme:** light, Bootstrap ("Flatly"-style), one sans-serif font throughout (Inter), recessive gray gridlines, no 3D, no chart borders.

**Fixed color encodings:** the same meaning always gets the same color, in every tab. Validated with the dataviz palette validator (colorblind separation, normal-vision distance, lightness, chroma).

| Meaning | Colors | Validation |
|---|---|---|
| Sex: Women / Men | violet `#6250d6` / aqua `#1baf7a` | ✅ pass (CVD ΔE 27) |
| Season: Summer / Winter | yellow `#eda100` / blue `#2a78d6` | ✅ pass (CVD ΔE 31) |
| Compared sports (Sports tab only, 1–4) | blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a`, plum `#9b2f8a` | ✅ pass, all 4 together (CVD ΔE 9.2) |
| Magnitude (choropleth, count heatmaps, map symbols) | sequential blue `#cde2fb` → `#0d366b` | one hue, light → dark |
| Gender timeline | gray = men only, violet = women also compete; current share written as text | same violet as "Women" |
| De-emphasis (unselected items) | gray `#b8b7b1` | emphasis pattern |
| Medals: Gold / Silver / Bronze | metallic: gold `#d4a20a`, silver `#7f8c99`, bronze `#a0522d`, **always with a text label** (G/S/B) and fixed order Gold → Silver → Bronze | ⚠ CVD ΔE 14.7 and normal-vision ΔE 17.5 pass; silver fails the chroma check by nature, so labels are mandatory |

Colors that are hard to read on white (yellow, aqua) are always paired with visible text labels or tooltips (the validator's "relief rule"). Color is never the only cue: legends are always present, and series of four or fewer are direct-labelled.

---

## 7. What is deliberately *not* included
* No pie or sunburst charts: shares are shown with a treemap, a spine chart or written percentages.
* No dual-axis charts.
* No country-color legend with 200 colors: countries are gray unless selected.
* No prediction or modelling beyond the descriptive PCA and the trend line on the size-and-wealth scatter.
* No chart that repeats another chart's answer (see §9).

---

## 8. Review decisions (2026-11-12, old numbering)
| Topic | Decision |
|---|---|
| Medal colors | Metallic colors, always paired with a text label and fixed order (recognisable convention; label covers the gray-silver weakness) |
| Map default | Total over the year range, plus a toggle for one-Games-at-a-time with slider and ▶ play |
| Scope | All 5 tabs and questions Q1.1–Q5.3 kept as designed |
| Country selection | Highlight on the Countries tab, filter on all other tabs |
| FT Visual Vocabulary (added 2026-11-12) | Use the FT Visual Vocabulary as the chart reference; cover all 9 categories |
| Deviation | Q4.3 dumbbell → **spine chart** |
| Spatial | Totals → **proportional-symbol map**; rates → **choropleth** |
| Part to whole | Sunburst → **treemap** |
| Flow | New **Sankey** of national-team switches (Q2.6) |
| Distribution | New **age–sex population pyramid** (Q4.4) |
| Historic teams on the map (Phase 5b) | Own circle at the main successor's location (D15), e.g. USSR, Unified Team and ROC as separate circles at Russia |
| Rank-based charts (Q2.2, Q2.5) | Compare one season at a time: with Season = Both they show the Summer Games, with a note |
| Specialisation index | Zero medals in a sport are shown blank, not as "strongly weaker" |
| Physique counting unit (Phase 5c) | Height, weight and BMI: each athlete once per sport (latest Games in the filter). Age: once per Games |
| Minimum sample (Phase 5c) | A box or violin needs 30+ measured athletes; a Games on the trend chart needs 8+ |
| Focus sport (Phase 5c) | Set by clicking a sport in Q3.1 or by a menu; drives Q3.2–Q3.4. The trend reference ("all sports") uses the focus sport's season only |
| Gender milestones (Phase 5d) | Only milestones confirmed in the data are labelled. Not labelled: "2012, every country sent women" (3 teams had no women in this data) and women's gymnastics in 1900 (contradicts the historical record, probably a data quirk) |
| Gender heatmap (Phase 5d) | Cells with fewer than 10 athletes are blank; sports ordered by the decade women first took part |
| DNS-only athletes (Phase 5d) | Not counted as participants (D16), applied to every tab |
| Sport similarity (Phase 5e) | PCA on standardised sport profiles (mean height, weight, BMI, age, % women), recomputed for the filters. Axes are named automatically from their strongest loadings (default: axis 1 = size, 57 %; axis 2 = age, 18 %). With a Sex filter set, % women is dropped |
| Compared sports (Phase 5e) | 2–4 sports; a 5th click drops the oldest pick (with a message); a lasso keeps the 4 largest sports. Each sport keeps its colour while it stays selected; a newcomer takes a freed colour |
| Robustness (Phase 6) | Automated sweep: 17 awkward filter combinations × 42 chart variants (714 cases) must never raise; empty states must name the real reason |
| Performance (Phase 6) | Only the visible tab recomputes on a filter change (`tab_callback`); filtered rows and sport profiles cached per filter |
| Safety net (Phase 6) | If a chart callback ever fails, the card shows "This chart could not be drawn" and the error is logged; the rest of the page keeps working |
| Filter bar (Phase 6) | A line above the tabs always states the active filters and the current tab's exceptions |

---

## 9. Simplification (2026-11-13, Phase 8 numbering)
A review of the finished dashboard found it crowded: some charts repeated another chart's answer, some were hard to read, and the filter sidebar took a fixed column of the screen. Decisions:

| Change | Reason |
|---|---|
| Sidebar → round floating **filter button** + slide-in panel; badge counts active filters | The filters are set once in a while; the charts get the full width the rest of the time |
| Removed Overview **stacked area** (old Q1.2) | The women/men split over time is answered better on the Gender tab (Q4.1). The treemap takes the full width instead, and a treemap click now narrows the athlete table |
| Removed **bump chart** (old Q2.2) | The scatter (now Q2.2) takes its place; who dominated which era is still visible on the map's ▶ play mode |
| Removed **Sankey** (old Q2.6) | Few readers need the team-switch flows; the Flow category is no longer covered (§3a) |
| Heatmap (now Q2.4) combines historic teams with their successor | URS/RUS or FRG/GDR/GER split over separate rows hid long-run national specialisations. The map (Q2.1) still keeps them apart, where the separation is part of the story. Mixed or joint teams (Australasia, West Indies Federation, Korea 2018) are not folded into one country |
| Removed **box plots** (old Q3.1) and the **box/lasso athlete table** | Sixty sorted boxes were the densest chart of the dashboard; the table added little beyond the density chart's hover. The focus sport is now chosen in a menu |
| Physiques order: trend first | "Have rowers got taller?" is the most telling physique question, so it is the first chart |
| Gender heatmap (old Q4.2) → **Priestley timeline** | In the sport × decade heatmap, all-men and all-women cells were solid colour blocks that were hard to read. The timeline shows when each sport opened to women and writes today's balance as a number (or "men only" / "women only") |
| Removed **population pyramid** (old Q4.4) | The age difference between women and men is small and gave no extra insight |
| Removed **radar** (old Q5.2) | It repeated the similarity map (same five measures); the violins show the real distributions |
| Map ignores the mouse wheel | The wider map captured page scrolling; zoom stays available in its toolbar |

---

## 10. Four analytical questions (2026-11-17)
Fifteen numbered questions made every chart look like its own analysis, including charts that only show the data (the headline numbers, the treemap, the athlete search). A dashboard reads better when it is built around a few clear questions, with each visualisation and interaction supporting one of them.

| Change | Reason |
|---|---|
| One question per analytical tab (Q1–Q4), stated in the tab header | Each tab tells one story; its charts are the evidence for different aspects of it (§2) |
| Overview has no question | KPI tiles, the programme treemap and the athlete search describe the data and are self-explanatory |
| Chart cards get plain titles instead of questions | The title says what is shown ("Home advantage: hosts at home vs usual"); the question lives once, at the top |
| Treemap groups each sport under its own season | Figure skating (1908, 1920) and ice hockey (1920) appeared under Summer because they were held at Summer Games before 1924. They are Winter sports, so they now sit under Winter; the hover notes the early Summer entries, and no entries are dropped |

---

## 11. Host question and icon rail (2026-11-17)
| Change | Reason |
|---|---|
| "Do hosts win more at home?" is its own question (**Q2**), with its own heading on the Countries tab; the later questions became Q3–Q5 | Home advantage is a clear yes/no question with a strong answer (28 of 29), worth presenting on its own rather than as one aspect of Q1 |
| Q1 narrowed to size, wealth or specialisation | Hosting moved to Q2 |
| Tabs → **left icon rail** with sport icons and short labels (Overview ◎ rings, Countries medal, Physiques runner, Gender ♀♂, Sports ball) | Frees the top of the page; the icons make the sections recognisable at a glance |
| Motion: the highlight slides (with a slight overshoot) to the active icon, the icon pops when chosen, icons lift on hover, and the opened tab fades up | Makes the navigation feel responsive; all motion is switched off when the system asks for reduced motion |
| Icons are local SVG files used as CSS masks | They work offline (no icon CDN needed) and take the theme colour of their state |

---

## 12. Visuals-only Overview and floating icons (2026-11-18)
| Change | Reason |
|---|---|
| Overview: removed the KPI number cards, the intro text and the "how to read" lines; the treemap is taller | The Overview should show the data, not describe it; the numbers are in the treemap and its hover |
| Kept the athlete search (box + table, no extra text) | It is the dashboard's name search, a key interaction; a treemap click still narrows it |
| Icon rail → icons floating in a translucent pill, names as hover tooltips | The fixed rail and its border took a column of the screen; the pill blends into the page |
| Header: slimmer, no bar, scrolls away with the page | More of the screen goes to the charts |

---

## 13. Top bar, Filters button and captions (2026-11-18)
| Change | Reason |
|---|---|
| Icons moved from the left edge to a translucent bar floating at the top centre; labels appear under the icons on hover | The left pill still took width from the charts; the top of the page is free once the title scrolls away |
| Filters button moved to the top right, in the same glass style as the icon bar | One visual language for all controls |
| The filter panel grows out of the button and collapses back into it | The panel's origin is obvious, and closing it returns to the same place |
| Filter controls restyled to match (pill tracks, rounded dropdowns, pill buttons) | Consistent with the icon bar |
| Tab captions removed; only rules the reader must know remain, with ⓘ (selected countries highlighted; Sex / Sports filter does not apply). The filter bar no longer repeats them | Less reading; each rule is said once, where it applies |
| Icon bar moved to the top right, just left of the Filters button and separate from it (2026-11-18) | All controls sit together in one corner; the rest of the top edge stays free |
