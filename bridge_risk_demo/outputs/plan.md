# Implementation Plan: `bridge_analysis.py`

## Scope

A single-file Python script that loads the 2025 Texas NBI dataset, computes a
composite structural risk score for every bridge, prints a terminal summary, and
saves four publication-quality figures. Runnable with `python bridge_analysis.py`.

---

## Module-Level Docstring

The script opens with a docstring stating:

- **Research question**: Which Texas bridges pose the greatest structural risk
  when accounting for physical condition, age beyond design life, and traffic
  exposure?
- **Data source**: FHWA National Bridge Inventory, 2025 Texas file
  (`bridge_risk_demo/bridges_texas.csv`). NBI items referenced: 3, 8, 16, 17,
  27, 29, 58, 59, 60, 62, 43A, 113.
- **Risk formula**:
  `risk_score = 0.20 * condition_risk + 0.60 * age_risk + 0.20 * traffic_risk`
- **Tier thresholds**: Low < 0.25, Moderate [0.25, 0.50), High [0.50, 0.75),
  Critical >= 0.75.

---

## Constants (top of file, after imports)

All file paths defined as `pathlib.Path` objects:

```
DATA_DIR   = Path("bridge_risk_demo")
INPUT_CSV  = DATA_DIR / "bridges_texas.csv"
OUTPUT_DIR = DATA_DIR / "outputs"
```

Figure filenames:

```
FIG1_PATH = OUTPUT_DIR / "fig1_risk_map.png"
FIG2_PATH = OUTPUT_DIR / "fig2_age_condition.png"
FIG3_PATH = OUTPUT_DIR / "fig3_risk_distribution.png"
FIG4_PATH = OUTPUT_DIR / "fig4_county_risk.png"
```

Analysis constants:

```
CURRENT_YEAR   = 2025
DESIGN_LIFE    = 50
FIGURE_DPI     = 150
```

Weight constants for the risk formula:

```
W_CONDITION = 0.30
W_AGE       = 0.30
W_TRAFFIC   = 0.40
```

Tier boundaries:

```
TIER_THRESHOLDS = [0.25, 0.50, 0.75]
TIER_LABELS     = ["Low", "Moderate", "High", "Critical"]
```

Column name constants (the exact NBI column headers used in `usecols`):

```
COLS = {
    "id":     "STRUCTURE_NUMBER_008",
    "county": "COUNTY_CODE_003",
    "lat":    "LAT_016",
    "lon":    "LONG_017",
    "year":   "YEAR_BUILT_027",
    "adt":    "ADT_029",
    "deck":   "DECK_COND_058",
    "super":  "SUPERSTRUCTURE_COND_059",
    "sub":    "SUBSTRUCTURE_COND_060",
    "culv":   "CULVERT_COND_062",
    "mat":    "STRUCTURE_KIND_043A",
    "scour":  "SCOUR_CRITICAL_113",
}
```

---

## STEP 1 -- Data Loading & Cleaning

### Functions

| Function | Purpose |
|----------|---------|
| `load_and_clean(path: Path) -> pd.DataFrame` | Read CSV, select columns, parse types, apply all cleaning filters, return analysis-ready DataFrame. |
| `parse_nbi_lat(raw: pd.Series) -> pd.Series` | Convert DDMMSSCC packed integers to decimal-degree latitudes. |
| `parse_nbi_lon(raw: pd.Series) -> pd.Series` | Convert DDDMMSSCC packed integers to negative decimal-degree longitudes. |

### Libraries / methods

- `pandas.read_csv` with `usecols=list(COLS.values())`, `quotechar="'"`,
  `dtype=str` (load everything as string first to avoid misinterpretation of
  condition codes like `"0"` or `"N"`).
- `pd.to_numeric(..., errors="coerce")` for condition rating columns -- converts
  `"0"`--`"9"` to int and `"N"` to `NaN` in one pass.
- `Series.astype(int)` for `YEAR_BUILT_027` and `ADT_029` after validation.
- Integer division / modulo arithmetic for coordinate parsing (no regex needed).

### Cleaning logic (applied in order)

1. **Parse condition ratings to numeric.** For each of the four condition
   columns (deck, super, sub, culvert), use `pd.to_numeric(errors="coerce")`.
   Values `"N"` become `NaN`.

2. **Compute `min_cond`.** For each row, take the minimum of the four condition
   columns ignoring NaN: `df[cond_cols].min(axis=1)`. This handles the
   bridge/culvert split naturally -- bridges will min over deck/super/sub
   (culvert is NaN), culverts will use the culvert rating alone.

3. **Drop rows where `min_cond` is NaN.** These are the ~15 edge-case records
   where all four condition columns might be non-numeric. Expected loss: ~0
   records based on the data description (every record has at least one numeric
   rating).

4. **Filter condition ratings to [0, 9].** Drop any row where `min_cond` falls
   outside this range. Per the data description, no such rows exist, but the
   guard is defensive.

5. **Parse `YEAR_BUILT_027` to int.** Filter to [1800, 2025]. Per the data
   description, all values are 1900--2025, so no rows should be lost.

6. **Parse `ADT_029` to int.** Drop rows where ADT < 0. *Keep* ADT = 0 rows
   in the DataFrame (they participate in risk scoring), but note that
   `log1p(0) = 0` so they will receive `traffic_risk = 0` naturally.

7. **Parse coordinates** via `parse_nbi_lat` / `parse_nbi_lon`. Add columns
   `latitude` and `longitude` (decimal degrees).

8. **Derive `age`** column: `CURRENT_YEAR - year_built`.

9. **Print a cleaning summary**: rows before, rows after, rows removed by each
   filter.

### Assumptions

- The file is comma-delimited with single-quote text qualifier (confirmed in
  data description).
- Every record has at least one numeric condition rating among the four columns.
  The ~15 ambiguous records (where bridge/culvert assignment is unclear) will
  be handled by the NaN-aware `min()`.

### Edge cases

- **Condition rating `"N"` vs `"0"`.** `"N"` means not applicable (wrong
  structure type); `"0"` is a valid worst-possible rating. `pd.to_numeric`
  handles this correctly: `"N"` -> NaN, `"0"` -> 0.
- **Coordinate edge cases.** Some raw lat/lon values could be zero or
  malformed. After parsing, sanity-check that lat is in [25, 37] and lon in
  [-107, -93] (Texas bounding box). Log and drop outliers.

### Pitfalls

- **Do not use `quotechar='"'` (double-quote).** This dataset uses single-quote
  as the text qualifier. Using the wrong quotechar will corrupt text fields
  containing commas.
- **Do not cast condition columns to int before handling `"N"`.** This will
  raise a ValueError. Must go through `pd.to_numeric(errors="coerce")` first.
- **`min(axis=1)` with all-NaN rows.** Pandas returns NaN for all-NaN rows
  (which is the desired behavior -- they get dropped). Do not use `skipna=False`
  accidentally.

---

## STEP 2 -- Risk Score Computation

### Functions

| Function | Purpose |
|----------|---------|
| `compute_condition_risk(min_cond: pd.Series) -> pd.Series` | Map minimum condition rating [0, 9] to condition risk [0, 1]. |
| `compute_age_risk(age: pd.Series) -> pd.Series` | Map bridge age to age risk [0, 1] using design-life normalisation. |
| `compute_traffic_risk(adt: pd.Series, max_adt: float) -> pd.Series` | Map ADT to traffic risk [0, 1] using log1p normalisation. |
| `compute_risk_score(df: pd.DataFrame) -> pd.DataFrame` | Orchestrator: calls the three risk functions, applies weights, assigns tiers. Returns df with new columns. |
| `assign_tier(risk_score: pd.Series) -> pd.Series` | Classify each risk_score into Low / Moderate / High / Critical using `pd.cut`. |

### Risk sub-score definitions

**condition_risk** (higher = worse condition):

```
condition_risk = (9 - min_cond) / 9
```

- min_cond = 9 (best) -> condition_risk = 0.0
- min_cond = 0 (worst) -> condition_risk = 1.0
- This is a simple linear inversion. No log transform needed because the
  rating scale is already ordinal on [0, 9].

**age_risk** (higher = older relative to design life):

```
age_risk = min(age / DESIGN_LIFE, 1.0)
```

- A bridge at exactly 50 years (the design life) has age_risk = 1.0.
- A bridge at 25 years has age_risk = 0.5.
- Bridges older than 50 years are capped at 1.0 (they cannot exceed maximum
  age risk). This avoids unbounded scores for the many pre-1975 structures.
- Use `np.clip(age / DESIGN_LIFE, 0, 1)` for vectorised capping.

**traffic_risk** (higher = more traffic exposure):

```
traffic_risk = log1p(adt) / log1p(max_adt)
```

- `max_adt` is derived as `df["ADT_029"].max()` from the *cleaned* dataset
  (observed max: 810,110).
- `np.log1p` is used because ADT spans five orders of magnitude (0 to 810k).
  Raw linear normalisation would compress 95%+ of bridges near zero. log1p
  compresses the long tail while preserving `log1p(0) = 0`.
- The division by `log1p(max_adt)` normalises to [0, 1].

**Composite risk_score:**

```
risk_score = 0.30 * condition_risk + 0.30 * age_risk + 0.40 * traffic_risk
```

The traffic weight (0.40) is highest to emphasise public safety consequence --
a failing bridge carrying heavy traffic poses greater risk than one with low
exposure.

**Tier classification:**

| Tier | risk_score range |
|------|-----------------|
| Low | [0, 0.25) |
| Moderate | [0.25, 0.50) |
| High | [0.50, 0.75) |
| Critical | [0.75, 1.0] |

Use `pd.cut(risk_score, bins=[-0.001, 0.25, 0.50, 0.75, 1.001], labels=TIER_LABELS)`.
The slightly expanded bin edges (-0.001 and 1.001) ensure that exact boundary
values (0.0 and 1.0) are captured.

### New columns added to DataFrame

- `min_cond` (float, 0--9)
- `age` (int)
- `condition_risk` (float, 0--1)
- `age_risk` (float, 0--1)
- `traffic_risk` (float, 0--1)
- `risk_score` (float, 0--1)
- `risk_tier` (Categorical: Low / Moderate / High / Critical)

### Assumptions

- The weighted formula and tier thresholds are taken directly from the user's
  specification.
- `max_adt` is computed from the cleaned data, not a hardcoded value. This
  makes the script robust if applied to a different state.

### Edge cases

- **ADT = 0**: `log1p(0) = 0`, so traffic_risk = 0. These bridges still get
  valid risk scores from condition and age components.
- **Newly built bridges (age = 0)**: age_risk = 0.0. Combined with likely-good
  condition ratings, these will score very low risk. Correct behavior.
- **All three sub-scores at maximum** (min_cond = 0, age >= 50, max ADT):
  risk_score = 0.20(1.0) + 0.60(1.0) + 0.20(1.0) = 1.0. The formula is
  bounded.

### Pitfalls

- **Forgetting to cap age_risk at 1.0.** Without capping, a 125-year-old
  bridge would get age_risk = 2.5, pushing risk_score above 1.0 and breaking
  the tier classification. The `np.clip` is essential.
- **Using `log` instead of `log1p`.** `log(0)` is negative infinity.
  `log1p(0) = 0`. Always use `log1p` for ADT.
- **Integer division.** `9 - min_cond` and `age / DESIGN_LIFE` must be float
  division. Since `min_cond` comes from `pd.to_numeric` (returns float64 due
  to NaN handling) and `DESIGN_LIFE` is an int denominator in Python 3, this
  is safe by default. But add a comment noting the assumption.

---

## STEP 3 -- Terminal Summary

### Functions

| Function | Purpose |
|----------|---------|
| `print_summary(df: pd.DataFrame) -> None` | Print the full terminal report to stdout. |

### Printed output (in order)

1. **Header banner**:
   ```
   ══════════════════════════════════════════════════
   TEXAS BRIDGE RISK ANALYSIS — 2025 NBI DATA
   ══════════════════════════════════════════════════
   ```

2. **Dataset size**: `Total bridges analysed: {n:,}`

3. **Risk score statistics**:
   - Mean risk score (2 decimal places)
   - Median risk score (2 decimal places)

4. **Tier distribution table**:
   ```
   Tier        Count     %
   ─────────────────────────
   Low         X,XXX   XX.X%
   Moderate    X,XXX   XX.X%
   High        X,XXX   XX.X%
   Critical    X,XXX   XX.X%
   ```
   Use `value_counts()` on `risk_tier`, reindex by `TIER_LABELS` to enforce
   order. Compute percentages as `count / total * 100`.

5. **Poor-condition count**: Number and percentage of bridges with
   `min_cond <= 4` (FHWA "Poor" threshold per the Recording and Coding Guide).

6. **Oldest bridge**: Year built, structure number, and location
   (`FEATURES_DESC_006A` or `FACILITY_CARRIED_007` -- whichever is more
   descriptive). Use `df.loc[df["age"].idxmax()]`.

7. **Top-5 highest-risk bridges table**:
   ```
   Rank  Structure ID       County  Year  ADT      MinCond  Risk Score  Tier
   ────  ─────────────────  ──────  ────  ───────  ───────  ──────────  ────────
   1     XXXX               XXX     XXXX  XXX,XXX  X        0.XX        Critical
   ...
   ```
   Use `df.nlargest(5, "risk_score")`. Format ADT with thousands separators.

### Libraries / methods

- Plain `print()` with f-strings. No tabulate dependency.
- `df["risk_tier"].value_counts()`, `df["risk_score"].mean()`,
  `df["risk_score"].median()`.

### Assumptions

- The FHWA defines "Poor" as a lowest condition rating of 4 or below. This is
  the standard NBI definition used in the FHWA Bridge Condition reports.

### Pitfalls

- **Tier order.** `value_counts()` returns by frequency, not by label order.
  Must reindex with `TIER_LABELS` to get Low -> Moderate -> High -> Critical.
- **Ties in top-5.** `nlargest` is stable, but if multiple bridges share the
  same risk score, the table should still show exactly 5 rows. `nlargest(5)`
  handles this correctly by default.

---

## STEP 4 -- Figures

All figures use `matplotlib.pyplot` only (no seaborn, no plotly). Every figure
is saved with `dpi=150` via `fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")`.

### Figure 1: Risk Map (`fig1_risk_map.png`)

| Attribute | Detail |
|-----------|--------|
| **Function** | `plot_risk_map(df: pd.DataFrame, path: Path) -> None` |
| **Plot type** | Scatter plot: longitude (x) vs latitude (y), one point per bridge. |
| **Color** | Points colored by `risk_score` using `cmap="RdYlGn_r"` (red = high risk, green = low). The reversed RdYlGn is intuitive: red = danger. |
| **Size** | Fixed small marker size (`s=1` or `s=2`) to avoid overplotting with ~57k points. |
| **Alpha** | `alpha=0.5` to show density through overlap. |
| **Colorbar** | Horizontal colorbar below the plot, label: "Risk Score". Tick marks at 0.0, 0.25, 0.50, 0.75, 1.0 with tier labels annotated. |
| **Axes** | `xlabel="Longitude"`, `ylabel="Latitude"`. `set_aspect("equal")` to avoid geographic distortion. |
| **Title** | `"Texas Bridge Risk Map — 2025 NBI"` |

**Key calls:**
```python
fig, ax = plt.subplots(figsize=(10, 8))
sc = ax.scatter(df["longitude"], df["latitude"], c=df["risk_score"],
                cmap="RdYlGn_r", s=1, alpha=0.5, vmin=0, vmax=1)
cbar = fig.colorbar(sc, ax=ax, orientation="horizontal", pad=0.08, aspect=40)
```

**Non-obvious formatting:**
- `vmin=0, vmax=1` forces the colormap to span the full [0, 1] risk range
  regardless of the actual data spread. Without this, matplotlib auto-scales
  and the colors become misleading.
- `set_aspect("equal")` is important for geographic plots to prevent Texas from
  appearing squashed or stretched.

**Edge cases:**
- Any records with lat/lon outside the Texas bounding box (if they survived
  cleaning) would appear as outlier points. The coordinate sanity check in
  Step 1 prevents this.

### Figure 2: Age vs Condition (`fig2_age_condition.png`)

| Attribute | Detail |
|-----------|--------|
| **Function** | `plot_age_vs_condition(df: pd.DataFrame, path: Path) -> None` |
| **Plot type** | Scatter plot: `age` (x) vs `min_cond` (y). |
| **Color** | Points colored by `risk_score`, cmap `"RdYlGn_r"`. |
| **Size** | `s=2`, `alpha=0.3` (heavy overplotting expected at integer condition values). |
| **Axes** | `xlabel="Bridge Age (years)"`, `ylabel="Minimum Condition Rating"`. Y-axis ticks at integers 0--9 with FHWA descriptors as secondary labels: 9="Excellent", 7="Good", 5="Fair", 4="Poor", 0="Failed". |
| **Title** | `"Bridge Age vs. Structural Condition"` |
| **Annotation** | Horizontal dashed line at y=4 labeled `"FHWA Poor threshold"`. Vertical dashed line at x=50 labeled `"50-year design life"`. These divide the plot into four quadrants. |
| **Colorbar** | Vertical colorbar on right, label: "Risk Score". |

**Key calls:**
```python
ax.axhline(y=4, color="red", linestyle="--", linewidth=0.8, label="Poor threshold")
ax.axvline(x=DESIGN_LIFE, color="blue", linestyle="--", linewidth=0.8, label="Design life")
ax.set_yticks(range(10))
```

**Non-obvious formatting — FHWA tick labels:**
The y-axis has integer ticks 0--9. Rather than labeling every tick with its
FHWA description (cluttered), annotate only the key thresholds:
```python
fhwa_labels = {9: "Excellent", 7: "Good", 5: "Fair", 4: "Poor", 0: "Failed"}
ax.set_yticks(range(10))
ax.set_yticklabels([f"{i} — {fhwa_labels[i]}" if i in fhwa_labels else str(i)
                     for i in range(10)])
```

**Pitfall:**
- Condition ratings are integers, so points stack vertically at each rating
  level. The low alpha and small marker size are essential to reveal density
  patterns within each horizontal band.

### Figure 3: Risk Distribution (`fig3_risk_distribution.png`)

| Attribute | Detail |
|-----------|--------|
| **Function** | `plot_risk_distribution(df: pd.DataFrame, path: Path) -> None` |
| **Plot type** | Histogram of `risk_score` with tier-colored background bands. |
| **Histogram** | `ax.hist(df["risk_score"], bins=50, color="steelblue", edgecolor="white", linewidth=0.3)` |
| **Tier bands** | Vertical `axvspan` rectangles behind the histogram, one per tier: Low = green (alpha=0.08), Moderate = yellow (0.08), High = orange (0.08), Critical = red (0.08). Very low alpha so the histogram bars remain readable. |
| **Tier labels** | Text annotations centered in each band, near the top of the plot. |
| **Axes** | `xlabel="Risk Score"`, `ylabel="Number of Bridges"`. x-axis from 0 to 1. |
| **Title** | `"Distribution of Bridge Risk Scores"` |
| **Statistics** | Annotate mean and median as vertical lines: mean = dashed black, median = solid grey. Legend entries for both. |

**Key calls:**
```python
ax.axvspan(0, 0.25, color="green", alpha=0.08)
ax.axvspan(0.25, 0.50, color="gold", alpha=0.08)
ax.axvspan(0.50, 0.75, color="orange", alpha=0.08)
ax.axvspan(0.75, 1.0, color="red", alpha=0.08)
ax.axvline(df["risk_score"].mean(), color="black", linestyle="--", label="Mean")
ax.axvline(df["risk_score"].median(), color="grey", linestyle="-", label="Median")
```

**Pitfall:**
- If the histogram y-range is large, tier labels at a fixed y position may
  collide with bars. Place labels using `ax.get_ylim()[1] * 0.95` for
  adaptive positioning.

### Figure 4: County Risk (`fig4_county_risk.png`)

| Attribute | Detail |
|-----------|--------|
| **Function** | `plot_county_risk(df: pd.DataFrame, path: Path) -> None` |
| **Plot type** | Horizontal bar chart of the top 20 counties by mean risk score. |
| **County filtering** | Only include counties with >= 50 bridges to avoid small-sample noise. Compute `groupby("COUNTY_CODE_003").agg(mean_risk=("risk_score","mean"), count=("risk_score","size"))`. Filter `count >= 50`. Sort by `mean_risk` descending. Take top 20. |
| **Bars** | Horizontal bars (`ax.barh`). Color bars by mean risk score using `"RdYlGn_r"` colormap via `plt.cm.RdYlGn_r(mean_risk)` for each bar. |
| **Axes** | `xlabel="Mean Risk Score"`, `ylabel="County Code"`. x-axis from 0 to 1 (or auto). |
| **Annotations** | Bridge count shown at the end of each bar: `f"n={count}"` in small grey text. |
| **Title** | `"Top 20 Counties by Mean Bridge Risk Score (min. 50 bridges)"` |
| **Reference line** | Vertical dashed line at the statewide mean risk score, labeled. |

**Key calls:**
```python
colors = plt.cm.RdYlGn_r(county_df["mean_risk"])
ax.barh(county_df["county"], county_df["mean_risk"], color=colors)
ax.axvline(statewide_mean, color="black", linestyle="--", linewidth=0.8)
```

**Non-obvious formatting:**
- Use `ax.invert_yaxis()` so the highest-risk county is at the top.
- County codes are 3-digit strings (e.g., "113"). These are not intuitive on
  their own, but mapping all 254 Texas FIPS codes to names adds complexity
  outside the scope of this script. The axis label `"County FIPS Code"` makes
  the encoding clear.

**Pitfall:**
- Without the minimum-bridge filter, small counties with one or two bridges
  in poor condition dominate the chart (100% high-risk from n=2 is not
  meaningful).

---

## Code Quality Checklist

| Requirement | How it is addressed |
|-------------|---------------------|
| Module-level docstring | Research question, NBI item references, risk formula, and tier definitions stated at the top of the file. |
| Docstring on every function | Each of the ~10 functions gets a one-line docstring describing inputs, outputs, and purpose. |
| File paths as `pathlib.Path` constants | `DATA_DIR`, `INPUT_CSV`, `OUTPUT_DIR`, `FIG1_PATH`--`FIG4_PATH` defined at module level. No string paths in function bodies. |
| Comments on non-obvious calculations | Comment on: DDMMSSCC parsing arithmetic, why `log1p` not `log`, why age_risk is clipped, why `vmin/vmax` are pinned on scatter colormaps, the FHWA Poor threshold (<=4). |
| matplotlib only | No seaborn, plotly, or other visualisation libraries imported. |
| All figures saved at dpi=150 | `FIGURE_DPI = 150` constant used in every `savefig` call. |
| Runnable with `python bridge_analysis.py` | All logic gated behind `if __name__ == "__main__":` which calls a `main()` function. `main()` calls steps in sequence: load -> compute risk -> print summary -> save figures. |

---

## Function Inventory (in file order)

| # | Function | Lines (est.) |
|---|----------|-------------|
| 1 | `parse_nbi_lat(raw)` | 8 |
| 2 | `parse_nbi_lon(raw)` | 8 |
| 3 | `load_and_clean(path)` | 45 |
| 4 | `compute_condition_risk(min_cond)` | 4 |
| 5 | `compute_age_risk(age)` | 4 |
| 6 | `compute_traffic_risk(adt, max_adt)` | 4 |
| 7 | `assign_tier(risk_score)` | 5 |
| 8 | `compute_risk_score(df)` | 15 |
| 9 | `print_summary(df)` | 40 |
| 10 | `plot_risk_map(df, path)` | 20 |
| 11 | `plot_age_vs_condition(df, path)` | 25 |
| 12 | `plot_risk_distribution(df, path)` | 25 |
| 13 | `plot_county_risk(df, path)` | 25 |
| 14 | `main()` | 15 |

**Estimated total: ~245 lines.**

---

## Dependencies

- `pandas` -- data loading and manipulation
- `numpy` -- `np.log1p`, `np.clip`, vectorised arithmetic
- `matplotlib` -- all figures
- `pathlib` -- file path handling (stdlib)

No external dependencies beyond the standard scientific Python stack.
