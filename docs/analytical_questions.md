# Dashboard Design: Analytical Questions, Charts and Interactions

Phase 3 design document. It fixes **what the dashboard must answer** and **why each chart is the right form for that question**, before any code is written. Chart types follow from the questions and from the shape of the data, never the other way round (see [REQUIREMENTS.md](../REQUIREMENTS.md)). Chart forms are named and checked against the course's reference, the **Financial Times *Visual Vocabulary*** (https://ft-interactive.github.io/visual-vocabulary/). Seven of its 9 categories are used (§3a).

**Status:** approved 2026-11-12; **simplified 2026-11-13** after a usability review: 21 questions became 15, charts that repeated another chart or gave little insight were removed, and the filter sidebar became a slide-in panel (§9). Questions are numbered in the order they appear on the page. Earlier review decisions are kept in §8 as a record and refer to the old numbering.

---

## 1. Purpose and users

**Purpose:** let a user explore 126 years of Olympic history from four perspectives (countries, bodies, gender, sports) and compare across time, place and discipline.

**Typical user:** a student, analyst or sports fan who has a question ("Did host countries really win more?", "Are rowers getting taller?") and wants to filter, compare and drill down rather than read a fixed report.

**Guiding principle:** overview first, then filter and zoom, then details on demand. Every tab opens on a meaningful default view. Filters narrow it, selections link the charts, and hover or a table gives the exact numbers.

---

## 2. The analytical questions

Each tab owns one theme. Questions are numbered so charts, interactions and the demo script can refer to them.

### Tab 1: Overview ("What is in the data?")
| # | Question |
|---|---|
| Q1.1 | How big are the Games in the current selection (athletes, countries, sports, events, medals)? |
| Q1.2 | How is the Olympic programme structured: which sports and events attract the most athletes? |
| Q1.3 | Who is a specific athlete, and what did they achieve? (search) |

### Tab 2: Countries & Medals ("Who wins, and why?")
| # | Question |
|---|---|
| Q2.1 | Where in the world are medals won, and how does the map change from Games to Games? |
| Q2.2 | Is success just a matter of size and wealth? Which countries over- or under-perform relative to population and GDP? |
| Q2.3 | Do host countries win more at their home Games? |
| Q2.4 | In which sports does each country specialise? |

### Tab 3: Athlete Physiques ("What body does each sport select for?")
| # | Question |
|---|---|
| Q3.1 | Have athletes in a sport become taller, heavier or older over the decades? |
| Q3.2 | Where does a chosen sport sit among all Olympians in height × weight? |
| Q3.3 | Do medallists differ physically from other competitors in the same sport? |

### Tab 4: Gender Participation ("How did women enter the Games?")
| # | Question |
|---|---|
| Q4.1 | How did women's share of athletes evolve in the Summer and Winter Games, and which milestones mark that change? |
| Q4.2 | When did each sport open to women, and how balanced is it now? |
| Q4.3 | Which countries send balanced teams, and which have large gender gaps? |

### Tab 5: Sport Comparison ("Which sports are alike?")
| # | Question |
|---|---|
| Q5.1 | Which sports have similar athletes, so that sports cluster into "families" of body type, age and gender mix? |
| Q5.2 | For 2–4 chosen sports, how different are their athletes' full distributions (not only averages)? |

---

## 3. Charts per question, and why each form

Forms are chosen from the data's job (magnitude, distribution, relationship, geography, hierarchy, change). Not one of the main analytical charts is a plain bar, line or pie chart.

### Tab 1: Overview
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q1.1 | **KPI tiles** (5 numbers, change vs the previous Games where one Games is selected) | Single headline values are not a chart's job | athlete_games, country_games |
| Q1.2 | **Treemap** (full width): Season → Sport → Event, sized by number of athlete entries; click a sport to zoom into its events | The programme is a strict hierarchy. FT recommends the treemap for hierarchical part-to-whole (and advises against the sunburst), and rectangles make sizes easier to compare | athlete_events |
| Q1.3 | **Searchable athlete table** (name search, sortable, paged) plus an **athlete card** on row click: bio, every Games, events, medals | Searching for a named individual is a lookup task, which a table does best | athlete_games, athlete_events |

### Tab 2: Countries & Medals
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q2.1 | **World map, two encodings by metric**: medal **totals → proportional-symbol map** (circle size = medals); **rates** (per million people / per $100bn GDP) **→ choropleth**. Default: totals over the filter's year range; a toggle switches to one Games at a time with a slider and ▶ play control. Historic teams keep their own circle (D15) | Geography is the point of the question. FT rule: choropleths show rates, totals belong on proportional symbols (shading big countries by raw totals exaggerates them by land area) | country_games |
| Q2.2 | **Bubble scatter**: x = GDP (log), y = medals (log), size = population, one bubble per country for the chosen Games; dashed trend line | Relationship between two continuous variables over orders of magnitude needs a log-log scatter. Distance from the trend line *is* over/under-performance | country_games (1960+) |
| Q2.3 | **Dumbbell**: each host nation's medal share at its home Games vs its average share in the neighbouring Games (±2), with a one-line summary | Before → after comparison per item is the canonical dumbbell job | country_games.is_host |
| Q2.4 | **Heatmap**: countries (rows) × sports (columns). Toggle: medal count ↔ **specialisation index** (country's share of medals in a sport ÷ its share of all medals; >1 = specialised). **Historic teams are combined with their successor** (USSR, Unified Team, ROC → Russia; East/West Germany, Saar → Germany; …), marked * | Two categorical dimensions with a magnitude per cell. The index removes the "big countries win everything" effect. A specialisation is a long-run trait of a sporting nation, so splitting it across flags would hide it | medals_by_sport + `da.lineage()` |

### Tab 3: Athlete Physiques
One measure switch (Height / Weight / BMI / Age) and one **focus sport** menu drive all three charts.

| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q3.1 | **Trend with uncertainty band** (full width): median (line) and interquartile range (band) per Games for the focus sport, women and men; dashed = all sports of the same season; sample size *n* on hover | Change over time with spread. The band shows whether shifts exceed the normal variation; *n* exposes thin early data (D11) | athlete_games |
| Q3.2 | **2D density contour** of height × weight for all athletes (gray), with the focus sport's athletes overlaid as points | 100k+ points overplot; a density shows where athletes concentrate, and the overlay places one sport inside the whole | athlete_games |
| Q3.3 | **Split violin**: medallists vs non-medallists in the focus sport | Two distributions compared head-to-head; a split violin puts them back-to-back on one axis | athlete_games |

### Tab 4: Gender Participation
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q4.1 | **Line of women's share (%)** per Games, Summer and Winter, with **annotated milestones** and a 50 % parity reference line; a followed sport is added as a dotted line | One measure over time; annotations turn it into an explanation | participation |
| Q4.2 | **Priestley timeline**: one row per sport still on the programme, from its first to its latest Games; gray = men only, violet = women also compete; a dot marks the first Games with women; the share of women at the latest Games is written at the end of the row ("men only" / "women only" in words) | The question is *when* something started and how long it has lasted, which is what a timeline of bars shows. Writing the current share as text avoids the problem of the former sport × decade heatmap, where all-men and all-women decades were solid colour blocks that said little | athlete_games |
| Q4.3 | **Spine chart per country**: each delegation as one bar split into women (left, violet) and men (right, aqua) around a 50 % parity line; top 25 delegations, sorted by imbalance | FT *Deviation*: the spine chart is listed for exactly this "split one value into Male/Female" case. Distance from the centre line *is* the gender gap | athlete_games |

### Tab 5: Sport Comparison
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q5.1 | **Sport similarity map**: PCA of the standardised sport profiles (mean height, weight, BMI, age, % female). Each sport is a point sized by athlete count, shaped by season, gray unless selected; axis loadings shown | Many variables per item reduced to 2D so that *distance = similarity*. Clusters emerge visually (power sports, endurance, small-and-light, tall team sports) | sport_profiles (recomputed for the filter) |
| Q5.2 | **Overlaid distributions** (small multiples: height, weight, age): one translucent violin per selected sport, median marked | Averages hide the overlap. The distributions show how distinct the sports really are | athlete_games |

**Chart-type inventory:** KPI tiles, treemap, table, proportional-symbol map, choropleth, bubble scatter (log-log), heatmap, dumbbell, trend band (fan), 2D density, split violin, annotated line, Priestley timeline, spine chart, PCA scatter, overlaid violins. That is 16 forms for 15 questions.


### 3a. Coverage of the FT Visual Vocabulary

The FT chart names are in *italics*.

| FT category | FT definition (short) | Our chart(s) | Question |
|---|---|---|---|
| **Deviation** | variation (+/−) from a reference point | *spine chart*: women vs men around 50 % parity; diverging specialisation index | Q4.3, Q2.4 |
| **Correlation** | relationship between two or more variables | *bubble*: medals vs GDP vs population; *XY-heatmap*: country × sport; *scatterplot*: PCA similarity map; height × weight density | Q2.2, Q2.4, Q5.1, Q3.2 |
| **Change v Time** | changing trends | *line* with annotations; *fan*: median + IQR band over time; *Priestley timeline* | Q4.1, Q3.1, Q4.2 |
| **Distribution** | values and how often they occur | *violin* (split and overlaid), *dot-plot* (dumbbell) | Q3.3, Q5.2, Q2.3 |
| **Part to whole** | an entity broken into components | *treemap* (Season → Sport → Event) | Q1.2 |
| **Magnitude** | size comparisons | *proportional symbols*; KPI tiles | Q2.1, Q1.1 |
| **Spatial** | geographical patterns | *proportional-symbol* map (totals); *basic choropleth* (rates) | Q2.1 |
| Ranking | position in an ordered list | not a chart of its own any more: only ordered rows (spine chart by imbalance, heatmap by medal total) | (Q4.3, Q2.4) |
| Flow | volumes moving between states | **not covered** since the Sankey was removed (2026-11-13) | — |

---

## 4. Interactions

### 4.1 Global filters (slide-in panel)
The filters live in a panel that slides in from the right when the round **filter button** (bottom right, always visible) is pressed, and closes with ×. The charts update while it is open, and the filters stay applied when it is closed. A badge on the button counts the active filters, and the **Showing:** bar above the tabs always lists them.

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
┌───────────────────────────────────────────────────────────────────────────┐
│  Olympic Athletes Explorer · 1896–2022                          [About]   │
├───────────────────────────────────────────────────────────────────────────┤
│ Showing: 1896–2022 · Summer and Winter · Women and men                    │
│ [Overview] [Countries] [Physiques] [Gender] [Sports]                      │
├───────────────────────────────────────────────────────────────────────────┤
│  Question line, e.g. "Q2.2 Is success just a matter of size and wealth?"  │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  main chart (full width)                                             │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────┐ ┌─────────────────────────────────┐ │
│  │  chart (≈ 7/12)                  │ │  chart (≈ 5/12)                 │ │
│  └──────────────────────────────────┘ └─────────────────────────────────┘ │
│  data note · source                                                 (⏷)  │ ← round filter button
└───────────────────────────────────────────────────────────────────────────┘
          (⏷) opens a filter panel that slides in over the right edge
```

* Each chart card carries its question number and a one-line "how to read" hint.
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
* No prediction or modelling beyond the descriptive PCA and the trend line in Q2.2.
* No chart that repeats another chart's answer (see §9).

---

## 8. Review decisions (2026-11-12, old numbering)
| Topic | Decision |
|---|---|
| Medal colors | Metallic colors, always paired with a text label and fixed order (recognisable convention; label covers the gray-silver weakness) |
| Map default | Total over the year range, plus a toggle for one-Games-at-a-time with slider and ▶ play |
| Scope | All 5 tabs and questions Q1.1–Q5.3 kept as designed |
| Country selection | Highlight on the Countries tab, filter on all other tabs |
| FT Visual Vocabulary (added 2026-11-12) | Use the course's FT reference; cover all 9 categories |
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

## 9. Simplification (2026-11-13)
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
