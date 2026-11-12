# Dashboard Design: Analytical Questions, Charts and Interactions

Phase 3 design document. It fixes **what the dashboard must answer** and **why each chart is the right form for that question**, before any code is written. Chart types follow from the questions and from the shape of the data, never the other way round (see [REQUIREMENTS.md](../REQUIREMENTS.md)).

**Status:** approved 2026-11-12. All tabs, questions and charts kept as designed; review decisions are recorded in §8.

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
| Q1.2 | How has participation grown over time, and how was it split between women and men? |
| Q1.3 | How is the Olympic programme structured: which sports and events attract the most athletes? |
| Q1.4 | Who is a specific athlete, and what did they achieve? (search) |

### Tab 2: Countries & Medals ("Who wins, and has that changed?")
| # | Question |
|---|---|
| Q2.1 | Where in the world are medals won, and how does the map change from Games to Games? |
| Q2.2 | Which countries dominated which eras, and when did leadership change hands (Cold War, boycotts 1980/84, the rise of China)? |
| Q2.3 | Is success just a matter of size and wealth? Which countries over- or under-perform relative to population and GDP? |
| Q2.4 | In which sports does each country specialise? |
| Q2.5 | Do host countries win more at their home Games? |

### Tab 3: Athlete Physiques ("What body does each sport select for?")
| # | Question |
|---|---|
| Q3.1 | How do height, weight, BMI and age differ between sports, for women and for men? |
| Q3.2 | How much do sports overlap in body type, and where does a chosen sport sit in the overall height × weight space? |
| Q3.3 | Have athletes in a sport become taller, heavier or older over the decades? |
| Q3.4 | Do medallists differ physically from other competitors in the same sport? |

### Tab 4: Gender Participation ("How did women enter the Games?")
| # | Question |
|---|---|
| Q4.1 | How did women's share of athletes evolve in the Summer and Winter Games, and which milestones mark that change? |
| Q4.2 | Which sports opened to women early or late, and which remain unbalanced? |
| Q4.3 | Which countries send balanced teams, and which have large gender gaps? |

### Tab 5: Sport Comparison ("Which sports are alike?")
| # | Question |
|---|---|
| Q5.1 | Which sports have similar athletes, so that sports cluster into "families" of body type, age and gender mix? |
| Q5.2 | For 2–4 chosen sports side by side, how do their athlete profiles compare? |
| Q5.3 | How do the full distributions (not only averages) of the chosen sports overlap? |

---

## 3. Charts per question, and why each form

Forms are chosen from the data's job (magnitude, distribution, relationship, geography, hierarchy, change). Not one of the main analytical charts is a plain bar, line or pie chart.

### Tab 1: Overview
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q1.1 | **KPI tiles** (5 numbers, change vs the previous Games where one Games is selected) | Single headline values are not a chart's job | athlete_games, country_games |
| Q1.2 | **Stacked area**: athletes per Games, Women / Men; Summer and Winter as two small panels | Part-to-whole over time. Stacking shows both the total and the split | participation |
| Q1.3 | **Sunburst**: Season → Sport → Event, sized by number of athlete entries; click to zoom into a sport | The programme is a strict hierarchy, and a sunburst shows both levels and their relative size in one view | athlete_events |
| Q1.4 | **Searchable athlete table** (name search, sortable, paged) plus an **athlete card** on row click: bio, every Games, events, medals | Searching for a named individual is a lookup task, which a table does best | athlete_games, athlete_events |

### Tab 2: Countries & Medals
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q2.1 | **Choropleth world map**: medals (or medals per million / per $100bn GDP). **Default: total over the sidebar's year range**; a toggle switches to one Games at a time with a slider and ▶ play control | The data has a geographic dimension; patterns by region are only visible on a map | country_games |
| Q2.2 | **Bump chart**: rank in the medal table per Games for the top 10 nations; all lines gray, selected countries highlighted | The question is about *rank changes*, not values, and a bump chart encodes exactly order over time. Gray-plus-highlight keeps 40 countries readable | country_games.rank |
| Q2.3 | **Bubble scatter**: x = GDP (log), y = medals (log), size = population, one bubble per country for the chosen Games; diagonal "expected" trend line | Relationship between two continuous variables over orders of magnitude needs a log-log scatter. Distance from the trend line *is* over/under-performance | country_games (1960+) |
| Q2.4 | **Heatmap**: countries (rows) × sports (columns). Toggle: medal count ↔ **specialisation index** (country's share of medals in a sport ÷ its share of all medals; >1 = specialised) | Two categorical dimensions with a magnitude per cell. The index removes the "big countries win everything" effect | medals_by_sport |
| Q2.5 | **Dumbbell**: each host nation's medal share at its home Games vs its average share in the neighbouring Games (±2) | Before → after comparison per item is the canonical dumbbell job | country_games.is_host |

### Tab 3: Athlete Physiques
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q3.1 | **Horizontal box plots per sport, sorted by median**; measure switch Height / Weight / BMI / Age; split by sex (two boxes per sport) | The task is comparing *distributions* across many (≈58) categories. Sorted boxes rank the sports while showing spread and outliers | athlete_games |
| Q3.2 | **2D density contour** of height × weight for all athletes (gray), with the selected sport's athletes overlaid as points; box/lasso select supported | 100k+ points overplot; a density shows where athletes concentrate, and the overlay places one sport inside the whole | athlete_games |
| Q3.3 | **Trend with uncertainty band**: median (line) and interquartile range (band) per Games, for the selected sports; sample size *n* on hover | Change over time with spread. The band shows whether shifts exceed the normal variation; *n* exposes thin early data (D11) | athlete_games |
| Q3.4 | **Split violin**: medallists vs non-medallists for the selected sport, per measure | Two distributions compared head-to-head; a split violin puts them back-to-back on one axis | athlete_games |

### Tab 4: Gender Participation
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q4.1 | **Line of women's share (%)** per Games, Summer and Winter, with **annotated milestones** (1900 first women; 1928 women's athletics; 2012 every NOC sends women) and a 50 % parity reference line | One measure over time; annotations turn it into an explanation. The single supporting line chart in the tab | participation |
| Q4.2 | **Heatmap sport × decade, female share** on a **diverging** scale centred at 50 % (gray = parity); blank = sport not held | Two ordered/categorical axes and a value with a natural midpoint (parity), so a diverging scale is the honest encoding | athlete_games |
| Q4.3 | **Dumbbell per country**: number of women vs men in the selected Games/range, sorted by gap; top 25 delegations | Comparing two values per item and the distance between them | country_games.n_female |

### Tab 5: Sport Comparison
| Q | Chart | Why this form | Data |
|---|---|---|---|
| Q5.1 | **Sport similarity map**: PCA of the standardised sport profiles (mean height, weight, BMI, age, % female). Each sport is a point sized by athlete count, shaped by season, gray unless selected; axis loadings shown | Many variables per item reduced to 2D so that *distance = similarity*. Clusters emerge visually (power sports, endurance, small-and-light, tall team sports) | sport_profiles (recomputed for the filter) |
| Q5.2 | **Radar chart**: z-scores of the 5 profile variables for the 2–4 selected sports | Multivariate profiles of a few items; the shape gives a quick "fingerprint" per sport. Kept to ≤ 4 sports for readability | sport_profiles |
| Q5.3 | **Overlaid distributions** (small multiples: height, weight, age): one translucent violin per selected sport | Averages hide the overlap. The distributions show how distinct the sports really are | athlete_games |

**Chart-type inventory:** KPI tiles, stacked area, sunburst, table, choropleth, bump chart, bubble scatter (log-log), heatmap (×2, sequential + diverging), dumbbell (×2), box plots, 2D density, trend band, split violin, annotated line, PCA scatter, radar, overlaid violins. That is 17 forms, each tied to a question.

---

## 4. Interactions

### 4.1 Global filter sidebar (left, always visible)
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
| Overview | click a sport in the sunburst | participation area chart shows that sport only |
| Overview | click an athlete row | athlete card opens |
| Countries | click a country on the map, bump chart or scatter | adds it to the selected countries; highlighted in all four charts |
| Countries | drag the Games slider / ▶ play | map and scatter show that Games |
| Physiques | click a sport's box | that sport is overlaid on the density plot and drives the trend and violin charts |
| Physiques | box/lasso select on the density plot | table below lists the selected athletes, with the count of each sport |
| Gender | click a heatmap cell | the line chart adds that sport's female-share trend |
| Sports | click or lasso sports on the similarity map | adds them to the comparison (max 4; oldest drops out); picker stays in sync |

### 4.3 Everywhere
* **Hover tooltips** with exact values and sample size *n*.
* **Zoom/pan** on all Cartesian charts (Plotly built-in), with double-click to reset.
* **Empty states:** "No athletes match these filters" instead of an empty or broken chart.
* **Data notes** under charts where needed: e.g. "GDP data from 1960 only", "Historic teams (USSR, GDR …) are not in World Bank data", "n = 412 athletes with known height".

---

## 5. Layout

```
┌───────────────────────────────────────────────────────────────────────────┐
│  🏅 Olympic Athletes Explorer · 1896–2022                       [About]   │
├──────────────┬────────────────────────────────────────────────────────────┤
│ FILTERS      │ [Overview] [Countries] [Physiques] [Gender] [Sports]       │
│              ├────────────────────────────────────────────────────────────┤
│ Years        │  Question line, e.g. "Q2.2 Which countries dominated …?"   │
│ ├──●────●──┤ │  ┌───────────────────────────┐ ┌────────────────────────┐ │
│ Season       │  │  main chart (2/3 width)   │ │ linked chart (1/3)     │ │
│ (Both|S|W)   │  │                           │ │                        │ │
│ Sex          │  └───────────────────────────┘ └────────────────────────┘ │
│ (All|W|M)    │  ┌──────────────────────────────────────────────────────┐ │
│ Sports  [▾]  │  │  secondary chart(s), full width                      │ │
│ Countries[▾] │  └──────────────────────────────────────────────────────┘ │
│ [Reset]      │  data note · source                                       │
└──────────────┴────────────────────────────────────────────────────────────┘
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
| Magnitude (map, count heatmaps) | sequential blue `#cde2fb` → `#0d366b` | one hue, light → dark |
| Female share (gender heatmap) | diverging: violet ← gray (50 %) → aqua | midpoint = parity |
| De-emphasis (unselected items) | gray `#b8b7b1` | emphasis pattern |
| Medals: Gold / Silver / Bronze | metallic: gold `#d4a20a`, silver `#7f8c99`, bronze `#a0522d`, **always with a text label** (G/S/B) and fixed order Gold → Silver → Bronze | ⚠ CVD ΔE 14.7 and normal-vision ΔE 17.5 pass; silver fails the chroma check by nature, so labels are mandatory |

Colors that are hard to read on white (yellow, aqua) are always paired with visible text labels or tooltips (the validator's "relief rule"). Color is never the only cue: legends are always present, and series of four or fewer are direct-labelled.

---

## 7. What is deliberately *not* included
* No pie charts: shares are shown with stacked areas, heatmaps or dumbbells.
* No dual-axis charts.
* No country-color legend with 200 colors: countries are gray unless selected.
* No prediction or modelling beyond the descriptive PCA and the trend line in Q2.3.

---

## 8. Review decisions (2026-11-12)
| Topic | Decision |
|---|---|
| Medal colors | Metallic colors, always paired with a text label and fixed order (recognisable convention; label covers the gray-silver weakness) |
| Map default | Total over the year range, plus a toggle for one-Games-at-a-time with slider and ▶ play |
| Scope | All 5 tabs and questions Q1.1–Q5.3 kept as designed |
| Country selection | Highlight on the Countries tab, filter on all other tabs |
