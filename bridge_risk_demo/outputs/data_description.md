# Texas Bridge Inventory -- Data Description

## 1. Dataset Overview

| Item | Value |
|------|-------|
| **Source** | Federal Highway Administration (FHWA) National Bridge Inventory |
| **State** | Texas (state code 48) |
| **Number of records** | 56,951 |
| **Number of columns** | 123 |
| **Year of data** | 2025 |
| **File size** | 22.2 MB |
| **Format** | Comma-separated values (CSV); text qualifier is single-quote (`'`) |
| **File path** | `bridge_risk_demo/bridges_texas.csv` |

The dataset contains one row per structure (bridges and culverts) on public roads in Texas, submitted to the FHWA under the National Bridge Inspection Standards.

---

## 2. Key Columns for Analysis

### 2.1 Structure Identifier

| Attribute | Value |
|-----------|-------|
| **Column name** | `STRUCTURE_NUMBER_008` |
| **NBI item** | 8 |
| **Description** | Unique identifier assigned by the state to each structure |
| **Data type** | String (alphanumeric, typically 15 characters) |
| **Unique values** | 56,951 (one per record -- confirms no duplicates) |
| **Missing** | 0 (0.00%) |

### 2.2 County

| Attribute | Value |
|-----------|-------|
| **Column name** | `COUNTY_CODE_003` |
| **NBI item** | 3 |
| **Description** | Three-digit FIPS county code within the state |
| **Data type** | String (zero-padded, 3 digits) |
| **Unique values** | 252 (of 254 Texas counties) |
| **Valid range** | `001`--`507` (odd numbers per FIPS convention) |
| **Missing** | 0 (0.00%) |

### 2.3 Coordinates

| Attribute | LAT_016 | LONG_017 |
|-----------|---------|----------|
| **NBI item** | 16 | 17 |
| **Description** | Latitude of the bridge | Longitude of the bridge |
| **Data type** | Integer (8 digits for lat, 9 for long) |
| **Missing** | 0 (0.00%) | 0 (0.00%) |
| **Encoding** | DDMMSSCC packed format | DDDMMSSCC packed format |

**Coordinate encoding: DDMMSSCC (degrees-minutes-seconds-centiseconds)**

The raw values are *not* decimal degrees. They use a packed integer format:

```
LAT:  DDMMSSCC    (8 digits)
LONG: DDDMMSSCC   (9 digits)
```

Where DD(D) = degrees, MM = minutes, SS = seconds, CC = hundredths of a second.

**Worked example** -- converting the first record:

```
Raw LAT_016 = 29362100

  DD = 29          (degrees)
  MM = 36          (minutes)
  SS = 21          (seconds)
  CC = 00          (centiseconds)

Decimal degrees = 29 + 36/60 + 21.00/3600
                = 29 + 0.6000 + 0.005833
                = 29.605833

Raw LONG_017 = 094272880

  DDD = 094        (degrees)
  MM  = 27         (minutes)
  SS  = 28         (seconds)
  CC  = 80         (centiseconds)

Decimal degrees = -(94 + 27/60 + 28.80/3600)
                = -(94 + 0.4500 + 0.008000)
                = -94.458000
```

Note: Texas longitudes are west of the prime meridian, so the sign should be negated for mapping.

### 2.4 Year Built

| Attribute | Value |
|-----------|-------|
| **Column name** | `YEAR_BUILT_027` |
| **NBI item** | 27 |
| **Description** | Year the structure was originally built |
| **Data type** | Integer (4 digits) |
| **Valid range** | 1900--2025 (observed in this dataset) |
| **Mean** | 1980.6 |
| **Missing** | 0 (0.00%) |

### 2.5 Average Daily Traffic

| Attribute | Value |
|-----------|-------|
| **Column name** | `ADT_029` |
| **NBI item** | 29 |
| **Description** | Average daily traffic count (vehicles/day) |
| **Data type** | Integer |
| **Valid range** | 0--810,110 (observed) |
| **Mean** | 11,382 |
| **Missing** | 0 (0.00%) |

### 2.6 Deck Condition Rating

| Attribute | Value |
|-----------|-------|
| **Column name** | `DECK_COND_058` |
| **NBI item** | 58 |
| **Description** | Condition of the bridge deck (riding surface and structural deck) |
| **Data type** | Single character |
| **Valid values** | `0`--`9` (worst to best) or `N` (not applicable -- culverts) |
| **Missing** | 0 (0.00%) |

Distribution:

| Rating | Count | % |
|--------|------:|----:|
| 9 | 125 | 0.2% |
| 8 | 3,249 | 5.7% |
| 7 | 22,584 | 39.7% |
| 6 | 8,401 | 14.8% |
| 5 | 1,063 | 1.9% |
| 4 | 108 | 0.2% |
| 3 | 7 | 0.0% |
| 2 | 1 | 0.0% |
| 1 | 1 | 0.0% |
| N | 21,412 | 37.6% |

### 2.7 Superstructure Condition Rating

| Attribute | Value |
|-----------|-------|
| **Column name** | `SUPERSTRUCTURE_COND_059` |
| **NBI item** | 59 |
| **Description** | Condition of the main structural members (beams, girders, trusses) |
| **Data type** | Single character |
| **Valid values** | `0`--`9` or `N` (not applicable -- culverts) |
| **Missing** | 0 (0.00%) |

### 2.8 Substructure Condition Rating

| Attribute | Value |
|-----------|-------|
| **Column name** | `SUBSTRUCTURE_COND_060` |
| **NBI item** | 60 |
| **Description** | Condition of piers, abutments, piles, and footings |
| **Data type** | Single character |
| **Valid values** | `0`--`9` or `N` (not applicable -- culverts) |
| **Missing** | 0 (0.00%) |

### 2.9 Culvert Condition

| Attribute | Value |
|-----------|-------|
| **Column name** | `CULVERT_COND_062` |
| **NBI item** | 62 |
| **Description** | Condition of the culvert (alignment, settlement, joints, scour) |
| **Data type** | Single character |
| **Valid values** | `0`--`9` or `N` (not applicable -- bridges) |
| **Missing** | 0 (0.00%) |

Note: Condition ratings 58--62 are mutually exclusive by structure type. Bridges use items 58/59/60 (deck/superstructure/substructure) with item 62 = `N`. Culverts use item 62 with items 58/59/60 = `N`. This dataset contains **35,554 bridges** and **21,412 culverts** (with 15 records being minor exceptions).

### 2.10 Main Span Material

| Attribute | Value |
|-----------|-------|
| **Column name** | `STRUCTURE_KIND_043A` |
| **NBI item** | 43A |
| **Description** | Material of the main span |
| **Data type** | Single digit |
| **Missing** | 0 (0.00%) |

| Code | Material | Count | % |
|------|----------|------:|----:|
| 1 | Concrete | 28,446 | 49.9% |
| 5 | Prestressed concrete | 19,207 | 33.7% |
| 3 | Steel | 3,830 | 6.7% |
| 4 | Steel continuous | 2,982 | 5.2% |
| 2 | Concrete continuous | 1,700 | 3.0% |
| 7 | Wood or Timber | 287 | 0.5% |
| 6 | Prestressed concrete continuous | 284 | 0.5% |
| 8 | Masonry | 121 | 0.2% |
| 0 | Other | 69 | 0.1% |
| 9 | Aluminum/Wrought/Cast Iron | 25 | 0.0% |

### 2.11 Scour Criticality

| Attribute | Value |
|-----------|-------|
| **Column name** | `SCOUR_CRITICAL_113` |
| **NBI item** | 113 |
| **Description** | Vulnerability of the bridge foundation to scour (erosion by flowing water) |
| **Data type** | Single character |
| **Valid values** | `0`--`9`, `N`, `U` (codes 0--3 = scour-critical) |
| **Missing** | 0 (0.00%) |

| Code | Meaning | Count | % |
|------|---------|------:|----:|
| 8 | Stable, above footing | 31,547 | 55.4% |
| N | Not applicable (culverts/tidal) | 10,457 | 18.4% |
| 5 | Stable, within limits of footing | 7,951 | 14.0% |
| 6 | Scour calculated, countermeasures installed | 3,321 | 5.8% |
| 4 | Foundations determined to be stable | 1,761 | 3.1% |
| 7 | Countermeasures installed, monitoring | 1,276 | 2.2% |
| 3 | **Scour-critical** | 516 | 0.9% |
| 2 | **Scour-critical** | 75 | 0.1% |
| 9 | Bridge on spread footings above water | 46 | 0.1% |
| 0 | **Unknown foundations / scour-critical** | 1 | 0.0% |

---

## 3. Data Quality Summary

### 3.1 Missing Values in Key Columns

**All 11 key analysis columns have zero missing values (0.00%).** The dataset is remarkably complete for the fields needed in a structural condition and traffic analysis.

Across all 123 columns, **15 columns are more than 50% empty**, but these are niche fields not needed for our analysis:

- `CRITICAL_FACILITY_006B` -- 0.0% filled
- `FRACTURE_LAST_DATE_093A` -- 1.5% filled
- `UNDWATER_LAST_DATE_093B` -- 1.5% filled
- `SPEC_LAST_DATE_093C` -- 0.0% filled
- `YEAR_OF_IMP_097` -- 0.3% filled
- `OTHER_STATE_CODE_098A`, `OTHER_STATE_PCNT_098B`, `OTHR_STATE_STRUC_NO_099` -- <0.2% filled
- `TEMP_STRUCTURE_103` -- 0.0% filled
- `PIER_PROTECTION_111` -- 2.9% filled
- `MIN_NAV_CLR_MT_116` -- 1.7% filled
- `LRS_INV_ROUTE_013A`, `SUBROUTE_NO_013B` -- ~8.5% filled
- `WORK_PROPOSED_075A`, `WORK_DONE_BY_075B` -- ~18% filled

### 3.2 Out-of-Range Condition Ratings

No out-of-range values. All condition rating columns (items 58, 59, 60, 62) contain only valid values: digits `0`--`9` or `N`.

### 3.3 Implausible Year Built Values

No implausible values detected:
- No records with year before 1800
- No records with year after 2026
- No zero values
- Oldest recorded year: **1900** (5 structures)
- Newest recorded year: **2025**

### 3.4 Negative or Zero ADT Values

- **Zero ADT records: 20** (0.04%) -- these likely represent closed or very-low-volume structures
- **Negative ADT records: 0**
- All values are valid non-negative integers

### 3.5 Recommended Cleaning Steps Before Analysis

1. **Convert coordinates**: Parse `LAT_016` and `LONG_017` from DDMMSSCC packed format to decimal degrees. Negate longitude for western hemisphere.
2. **Handle `N` condition ratings**: When analysing condition ratings, filter or split by structure type. Use items 58/59/60 for bridges only (where `CULVERT_COND_062 = N`) and item 62 for culverts only (where `DECK_COND_058 = N`).
3. **Cast condition ratings to integer**: Convert `0`--`9` character ratings to integers for numerical analysis; treat `N` as `NaN`.
4. **Exclude or flag zero-ADT records**: The 20 records with `ADT_029 = 0` should be excluded from traffic-weighted analyses.
5. **Derive bridge age**: Compute `age = 2025 - YEAR_BUILT_027` for deterioration modelling.
6. **Strip single-quote text qualifiers**: Some text fields (e.g., `FEATURES_DESC_006A`, `FACILITY_CARRIED_007`) are wrapped in single quotes in the raw file. Remove these if processing as strings.

---

## 4. Five Observations for a Bridge Engineer

### Observation 1: Nearly half of Texas bridges have exceeded a 50-year design life

**24,951 structures (43.8%)** were built in 1975 or earlier, exceeding the conventional 50-year design life. Of these aging structures, 364 (1.5%) are rated in Poor condition -- a manageable percentage now, but the sheer volume of structures approaching end-of-life represents a growing asset management challenge.

### Observation 2: 18 high-traffic bridges carry over 50,000 vehicles/day in Poor condition

Of 3,036 bridges with ADT > 50,000, **18 are rated Poor**. These include segments of IH-45 and IH-35E in the Dallas--Fort Worth and Houston metros, several built in the late 1950s--1960s. The highest-traffic Poor-condition structure carries IH-35E with an ADT of 194,462 (built 1959, deck rating = 4).

### Observation 3: 592 bridges are scour-critical

**592 structures (1.0%)** have scour codes 0--3 (scour-critical), meaning their foundations are assessed as unstable or at risk of failure during a flood event. An additional 1,761 bridges (3.1%) have code 4, meaning they require monitoring. For a state with significant flood exposure, this warrants attention.

### Observation 4: Concrete dominates -- 83.6% of structures are concrete or prestressed concrete

Concrete (49.9%) and prestressed concrete (33.7%) account for the vast majority of the inventory. Steel structures total 11.9%, while timber (287 structures, 0.5%) and masonry (121, 0.2%) persist as legacy material types. The 25 aluminum/wrought iron/cast iron structures are likely historic.

### Observation 5: Rural counties show the highest Poor-condition rates

Among counties with at least 100 structures, the highest Poor-condition rates are in rural areas: **Limestone County (9.0%)**, **Houston County (7.6%)**, and **Polk County (7.5%)**. By contrast, Harris County (Houston) has the most Poor bridges by absolute count (37) but a rate of only 1.1% across its 3,261 structures. This urban-rural disparity likely reflects differences in inspection/maintenance funding.
