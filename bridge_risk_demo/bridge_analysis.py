"""
Texas Bridge Structural Risk Analysis — 2025 NBI Data

Research question: Which Texas bridges pose the greatest structural risk
when accounting for physical condition, age beyond design life, and traffic
exposure?

Data source: FHWA National Bridge Inventory, 2025 Texas file.
NBI items referenced: 3, 8, 16, 17, 27, 29, 58, 59, 60, 62, 43A, 113.

Risk formula:
    risk_score = 0.20 * condition_risk + 0.60 * age_risk + 0.20 * traffic_risk

    condition_risk = (9 - min_condition_rating) / 9
    age_risk       = clip(age / 50, 0, 1)
    traffic_risk   = log1p(ADT) / log1p(max_ADT)

Tier thresholds:
    Low      [0.00, 0.25)
    Moderate [0.25, 0.50)
    High     [0.50, 0.75)
    Critical [0.75, 1.00]
"""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import ConnectionPatch, FancyBboxPatch
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path("bridge_risk_demo")
INPUT_CSV = DATA_DIR / "bridges_texas.csv"
OUTPUT_DIR = DATA_DIR / "outputs"

FIG1_PATH = OUTPUT_DIR / "fig1_risk_map.png"
FIG2_PATH = OUTPUT_DIR / "fig2_age_condition.png"
FIG3_PATH = OUTPUT_DIR / "fig3_risk_distribution.png"
FIG4_PATH = OUTPUT_DIR / "fig4_county_risk.png"

TX_BOUNDARY = DATA_DIR / "texas_boundary.geojson"

CURRENT_YEAR = 2025
DESIGN_LIFE = 50
FIGURE_DPI = 150

MAJOR_CITIES = {
    "Houston":        (-95.3698, 29.7604),
    "Dallas":         (-96.7970, 32.7767),
    "San Antonio":    (-98.4936, 29.4241),
    "Austin":         (-97.7431, 30.2672),
    "Fort Worth":     (-97.3308, 32.7555),
    "El Paso":        (-106.4850, 31.7619),
}

ZOOM_CITIES = {
    "Houston":     {"center": (-95.37, 29.76), "radius": 0.55},
    "DFW":         {"center": (-97.06, 32.80), "radius": 0.65},
    "San Antonio": {"center": (-98.10, 29.95), "radius": 0.80},
}

W_CONDITION = 0.30
W_AGE = 0.30
W_TRAFFIC = 0.40

TIER_THRESHOLDS = [0.25, 0.50, 0.75]
TIER_LABELS = ["Low", "Moderate", "High", "Critical"]

COLS = {
    "id": "STRUCTURE_NUMBER_008",
    "county": "COUNTY_CODE_003",
    "lat": "LAT_016",
    "lon": "LONG_017",
    "year": "YEAR_BUILT_027",
    "adt": "ADT_029",
    "deck": "DECK_COND_058",
    "super": "SUPERSTRUCTURE_COND_059",
    "sub": "SUBSTRUCTURE_COND_060",
    "culv": "CULVERT_COND_062",
    "mat": "STRUCTURE_KIND_043A",
    "scour": "SCOUR_CRITICAL_113",
}

COND_COLS = [COLS["deck"], COLS["super"], COLS["sub"], COLS["culv"]]


# ---------------------------------------------------------------------------
# Step 1 — Data loading & cleaning
# ---------------------------------------------------------------------------


def parse_nbi_lat(raw: pd.Series) -> pd.Series:
    """Convert DDMMSSCC packed integers to decimal-degree latitudes."""
    raw = raw.astype(int)
    # DDMMSSCC: DD = degrees, MM = minutes, SS = seconds, CC = centiseconds
    dd = raw // 1_000_000
    mm = (raw % 1_000_000) // 10_000
    ss = (raw % 10_000) // 100
    cc = raw % 100
    return dd + mm / 60.0 + (ss + cc / 100.0) / 3600.0


def parse_nbi_lon(raw: pd.Series) -> pd.Series:
    """Convert DDDMMSSCC packed integers to negative decimal-degree longitudes."""
    raw = raw.astype(int)
    # DDDMMSSCC: DDD = degrees, MM = minutes, SS = seconds, CC = centiseconds
    ddd = raw // 10_000_00
    mm = (raw % 10_000_00) // 10_000
    ss = (raw % 10_000) // 100
    cc = raw % 100
    # Negate for western hemisphere
    return -(ddd + mm / 60.0 + (ss + cc / 100.0) / 3600.0)


def load_and_clean(path: Path) -> pd.DataFrame:
    """Load NBI CSV, select columns, parse types, apply cleaning filters."""
    df = pd.read_csv(
        path,
        usecols=list(COLS.values()),
        dtype=str,
        quotechar="'",
    )
    n_raw = len(df)

    # Parse condition ratings: '0'-'9' -> numeric, 'N' -> NaN
    for col in COND_COLS:
        df[col] = pd.to_numeric(df[col].str.strip(), errors="coerce")

    # Minimum condition across bridge (deck/super/sub) and culvert ratings
    df["min_cond"] = df[COND_COLS].min(axis=1)

    # Drop rows with no valid condition rating
    df = df.dropna(subset=["min_cond"])
    n_after_cond = len(df)

    # Guard: ensure min_cond is in [0, 9]
    df = df[df["min_cond"].between(0, 9)]
    n_after_range = len(df)

    # Parse year built, filter to [1800, current year]
    df[COLS["year"]] = pd.to_numeric(df[COLS["year"]], errors="coerce")
    df = df.dropna(subset=[COLS["year"]])
    df[COLS["year"]] = df[COLS["year"]].astype(int)
    df = df[df[COLS["year"]].between(1800, CURRENT_YEAR)]
    n_after_year = len(df)

    # Parse ADT, drop negatives
    df[COLS["adt"]] = pd.to_numeric(df[COLS["adt"]], errors="coerce")
    df = df.dropna(subset=[COLS["adt"]])
    df[COLS["adt"]] = df[COLS["adt"]].astype(int)
    df = df[df[COLS["adt"]] >= 0]
    n_after_adt = len(df)

    # Parse coordinates to decimal degrees
    df["latitude"] = parse_nbi_lat(df[COLS["lat"]])
    df["longitude"] = parse_nbi_lon(df[COLS["lon"]])

    # Sanity-check: Texas bounding box
    tx_mask = df["latitude"].between(25, 37) & df["longitude"].between(-107, -93)
    df = df[tx_mask]
    n_after_geo = len(df)

    # Derive bridge age
    df["age"] = CURRENT_YEAR - df[COLS["year"]]

    # Cleaning summary
    print("-- Data Cleaning Summary --")
    print(f"  Raw records loaded:          {n_raw:>7,}")
    print(f"  After condition filter:      {n_after_cond:>7,}")
    print(f"  After condition range [0,9]: {n_after_range:>7,}")
    print(f"  After year filter [1800,{CURRENT_YEAR}]: {n_after_year:>7,}")
    print(f"  After ADT filter (>= 0):     {n_after_adt:>7,}")
    print(f"  After geo bounding box:      {n_after_geo:>7,}")
    print(f"  Records removed:             {n_raw - n_after_geo:>7,}")
    print()

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 2 — Risk score computation
# ---------------------------------------------------------------------------


def compute_condition_risk(min_cond: pd.Series) -> pd.Series:
    """Map min condition rating [0,9] to condition risk [0,1]. Inverted: 9=best -> 0 risk."""
    return (9 - min_cond) / 9.0


def compute_age_risk(age: pd.Series) -> pd.Series:
    """Map bridge age to risk [0,1], capped at 1.0 at the 50-year design life."""
    return np.clip(age / DESIGN_LIFE, 0, 1)


def compute_traffic_risk(adt: pd.Series, max_adt: float) -> pd.Series:
    """Map ADT to risk [0,1] using log1p to compress the five-order-of-magnitude range."""
    return np.log1p(adt) / np.log1p(max_adt)


def assign_tier(risk_score: pd.Series) -> pd.Series:
    """Classify risk scores into Low / Moderate / High / Critical tiers."""
    return pd.cut(
        risk_score,
        bins=[-0.001, 0.25, 0.50, 0.75, 1.001],
        labels=TIER_LABELS,
    )


def compute_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all risk sub-scores, the weighted composite, and tier labels."""
    df["condition_risk"] = compute_condition_risk(df["min_cond"])
    df["age_risk"] = compute_age_risk(df["age"])

    max_adt = df[COLS["adt"]].max()
    df["traffic_risk"] = compute_traffic_risk(df[COLS["adt"]], max_adt)

    df["risk_score"] = (
        W_CONDITION * df["condition_risk"]
        + W_AGE * df["age_risk"]
        + W_TRAFFIC * df["traffic_risk"]
    )

    df["risk_tier"] = assign_tier(df["risk_score"])

    return df


# ---------------------------------------------------------------------------
# Step 3 — Terminal summary
# ---------------------------------------------------------------------------


def print_summary(df: pd.DataFrame) -> None:
    """Print risk analysis summary to stdout."""
    n = len(df)
    mean_risk = df["risk_score"].mean()
    median_risk = df["risk_score"].median()

    tier_counts = (
        df["risk_tier"]
        .value_counts()
        .reindex(TIER_LABELS, fill_value=0)
    )

    # FHWA defines Poor as lowest condition rating <= 4
    poor_count = (df["min_cond"] <= 4).sum()

    oldest = df.loc[df["age"].idxmax()]

    top5 = df.nlargest(5, "risk_score")

    print("=" * 54)
    print("  TEXAS BRIDGE RISK ANALYSIS  -  2025 NBI DATA")
    print("=" * 54)
    print()
    print(f"  Total bridges analysed:  {n:,}")
    print(f"  Mean risk score:         {mean_risk:.2f}")
    print(f"  Median risk score:       {median_risk:.2f}")
    print()

    print("  Risk Tier Distribution")
    print("  " + "-" * 36)
    print(f"  {'Tier':<12} {'Count':>8}  {'%':>7}")
    print("  " + "-" * 36)
    for tier in TIER_LABELS:
        count = tier_counts[tier]
        pct = count / n * 100
        print(f"  {tier:<12} {count:>8,}  {pct:>6.1f}%")
    print("  " + "-" * 36)
    print()

    print(f"  Poor-condition bridges (min rating <= 4):  "
          f"{poor_count:,}  ({poor_count / n * 100:.1f}%)")
    print()

    print(f"  Oldest bridge:")
    print(f"    Structure:  {oldest[COLS['id']]}")
    print(f"    County:     {oldest[COLS['county']]}")
    print(f"    Year built: {int(oldest[COLS['year']])}")
    print(f"    Age:        {int(oldest['age'])} years")
    print()

    print("  Top 5 Highest-Risk Bridges")
    print("  " + "-" * 76)
    print(f"  {'Rank':<5} {'Structure ID':<18} {'County':<8} {'Year':<6} "
          f"{'ADT':>8}  {'MinCond':>7}  {'Risk':>6}  {'Tier'}")
    print("  " + "-" * 76)
    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        print(
            f"  {rank:<5} {row[COLS['id']]:<18} {row[COLS['county']]:<8} "
            f"{int(row[COLS['year']]):<6} {int(row[COLS['adt']]):>8,}  "
            f"{int(row['min_cond']):>7}  {row['risk_score']:>6.3f}  "
            f"{row['risk_tier']}"
        )
    print("  " + "-" * 76)
    print()


# ---------------------------------------------------------------------------
# Step 4 — Figures
# ---------------------------------------------------------------------------


def _plot_bridges_on_ax(ax, df, cmap, norm, s=1, alpha=0.5):
    """Scatter bridge points onto an axis with consistent color mapping."""
    return ax.scatter(
        df["longitude"], df["latitude"],
        c=df["risk_score"], cmap=cmap, norm=norm,
        s=s, alpha=alpha, edgecolors="none", rasterized=True,
    )


def _draw_boundary(ax, boundary_gdf):
    """Draw the Texas state boundary outline on an axis."""
    boundary_gdf.boundary.plot(ax=ax, edgecolor="0.3", linewidth=0.6, zorder=0)


def _draw_cities(ax, fontsize=7, marker_size=20):
    """Plot major city markers and labels."""
    for city, (lon, lat) in MAJOR_CITIES.items():
        ax.plot(lon, lat, "k^", markersize=marker_size**0.5, zorder=5)
        ax.annotate(
            city, (lon, lat),
            textcoords="offset points", xytext=(5, 4),
            fontsize=fontsize, fontweight="bold",
            color="0.15", zorder=5,
        )


def plot_risk_map(df: pd.DataFrame, path: Path) -> None:
    """Risk map with Texas boundary, cities, and three metro zoom insets."""
    tx = gpd.read_file(TX_BOUNDARY)

    cmap = plt.cm.RdYlGn_r
    norm = plt.Normalize(vmin=0, vmax=1)

    # Layout: main map on the left, three zoom panels stacked on the right
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(
        3, 2, width_ratios=[3, 1],
        hspace=0.25, wspace=0.08,
        left=0.05, right=0.92, top=0.93, bottom=0.10,
    )

    ax_main = fig.add_subplot(gs[:, 0])

    # -- Main panel --
    _draw_boundary(ax_main, tx)
    sc = _plot_bridges_on_ax(ax_main, df, cmap, norm, s=3, alpha=0.8)
    _draw_cities(ax_main, fontsize=8, marker_size=25)

    ax_main.set_xlabel("Longitude")
    ax_main.set_ylabel("Latitude")
    ax_main.set_title("Texas Bridge Risk Map - 2025 NBI", fontsize=14, fontweight="bold")
    ax_main.set_aspect("equal")
    ax_main.set_xlim(-107.5, -93.0)
    ax_main.set_ylim(25.5, 37.0)

    # Colorbar below the main map
    cbar_ax = fig.add_axes([0.05, 0.04, 0.55, 0.02])
    cbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cbar_ax, orientation="horizontal",
    )
    cbar.set_label("Risk Score", fontsize=10)
    cbar.set_ticks([0.0, 0.25, 0.50, 0.75, 1.0])

    # -- Zoom inset panels --
    zoom_order = ["DFW", "Houston", "San Antonio"]
    zoom_titles = {
        "DFW": "Dallas - Fort Worth",
        "Houston": "Houston",
        "San Antonio": "San Antonio - Austin",
    }

    for idx, city_key in enumerate(zoom_order):
        ax_z = fig.add_subplot(gs[idx, 1])
        info = ZOOM_CITIES[city_key]
        cx, cy = info["center"]
        r = info["radius"]

        _draw_boundary(ax_z, tx)
        _plot_bridges_on_ax(ax_z, df, cmap, norm, s=6, alpha=0.85)

        # Mark cities that fall within this zoom window
        for city, (lon, lat) in MAJOR_CITIES.items():
            if cx - r <= lon <= cx + r and cy - r <= lat <= cy + r:
                ax_z.plot(lon, lat, "k^", markersize=4, zorder=5)
                ax_z.annotate(
                    city, (lon, lat),
                    textcoords="offset points", xytext=(4, 3),
                    fontsize=6, fontweight="bold", color="0.15", zorder=5,
                )

        ax_z.set_xlim(cx - r, cx + r)
        ax_z.set_ylim(cy - r, cy + r)
        ax_z.set_aspect("equal")
        ax_z.set_title(zoom_titles[city_key], fontsize=9, fontweight="bold")
        ax_z.tick_params(labelsize=7)

        # Draw a rectangle on the main map showing the zoom extent
        rect = plt.Rectangle(
            (cx - r, cy - r), 2 * r, 2 * r,
            linewidth=1.2, edgecolor="0.25", facecolor="none",
            linestyle="--", zorder=4,
        )
        ax_main.add_patch(rect)

    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_age_vs_condition(df: pd.DataFrame, path: Path) -> None:
    """Scatter plot of bridge age vs minimum condition rating, colored by risk."""
    fig, ax = plt.subplots(figsize=(10, 7))

    sc = ax.scatter(
        df["age"], df["min_cond"],
        c=df["risk_score"], cmap="RdYlGn_r",
        s=2, alpha=0.3,
        vmin=0, vmax=1,
    )

    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("Risk Score")

    # FHWA Poor threshold at rating 4
    ax.axhline(y=4, color="red", linestyle="--", linewidth=0.8, label="Poor threshold (rating 4)")
    # 50-year design life reference
    ax.axvline(x=DESIGN_LIFE, color="blue", linestyle="--", linewidth=0.8, label="50-year design life")

    # FHWA descriptor labels on the y-axis
    fhwa_labels = {9: "Excellent", 7: "Good", 5: "Fair", 4: "Poor", 0: "Failed"}
    ax.set_yticks(range(10))
    ax.set_yticklabels(
        [f"{i} — {fhwa_labels[i]}" if i in fhwa_labels else str(i) for i in range(10)]
    )

    ax.set_xlabel("Bridge Age (years)")
    ax.set_ylabel("Minimum Condition Rating")
    ax.set_title("Bridge Age vs. Structural Condition")
    ax.legend(loc="lower left")

    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_risk_distribution(df: pd.DataFrame, path: Path) -> None:
    """Histogram of risk scores with tier-colored background bands."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Tier background bands (drawn first, behind histogram)
    tier_colors = ["green", "gold", "orange", "red"]
    tier_edges = [0.0, 0.25, 0.50, 0.75, 1.0]
    for i, label in enumerate(TIER_LABELS):
        ax.axvspan(tier_edges[i], tier_edges[i + 1], color=tier_colors[i], alpha=0.08)

    ax.hist(df["risk_score"], bins=50, color="steelblue", edgecolor="white", linewidth=0.3)

    # Tier labels positioned adaptively near the top
    y_top = ax.get_ylim()[1]
    for i, label in enumerate(TIER_LABELS):
        cx = (tier_edges[i] + tier_edges[i + 1]) / 2
        ax.text(cx, y_top * 0.95, label, ha="center", va="top",
                fontsize=9, fontstyle="italic", color="grey")

    # Mean and median reference lines
    ax.axvline(df["risk_score"].mean(), color="black", linestyle="--",
               linewidth=1, label=f"Mean ({df['risk_score'].mean():.2f})")
    ax.axvline(df["risk_score"].median(), color="grey", linestyle="-",
               linewidth=1, label=f"Median ({df['risk_score'].median():.2f})")

    ax.set_xlabel("Risk Score")
    ax.set_ylabel("Number of Bridges")
    ax.set_title("Distribution of Bridge Risk Scores")
    ax.set_xlim(0, 1)
    ax.legend()

    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_county_risk(df: pd.DataFrame, path: Path) -> None:
    """Horizontal bar chart of top-20 counties by mean risk score (min 50 bridges)."""
    fig, ax = plt.subplots(figsize=(10, 8))

    county_stats = (
        df.groupby(COLS["county"])["risk_score"]
        .agg(mean_risk="mean", count="size")
        .reset_index()
    )

    # Filter to counties with enough bridges to be statistically meaningful
    county_stats = county_stats[county_stats["count"] >= 50]
    county_stats = county_stats.nlargest(20, "mean_risk")

    # Sort ascending so highest-risk ends up at the top of the chart
    county_stats = county_stats.sort_values("mean_risk", ascending=True).reset_index(drop=True)

    mean_risk_vals = county_stats["mean_risk"].tolist()
    county_labels = county_stats[COLS["county"]].tolist()
    colors = plt.cm.RdYlGn_r(county_stats["mean_risk"].values)
    y_pos = list(range(len(county_stats)))
    ax.barh(y_pos, mean_risk_vals, color=colors)
    ax.set_yticks(y_pos, labels=county_labels)

    # Annotate each bar with bridge count
    for i, (_, row) in enumerate(county_stats.iterrows()):
        ax.text(
            row["mean_risk"] + 0.005, i,
            f"n={int(row['count'])}",
            va="center", fontsize=7, color="grey",
        )

    # Statewide mean reference line
    statewide_mean = df["risk_score"].mean()
    ax.axvline(statewide_mean, color="black", linestyle="--", linewidth=0.8,
               label=f"Statewide mean ({statewide_mean:.2f})")

    ax.set_xlabel("Mean Risk Score")
    ax.set_ylabel("County FIPS Code")
    ax.set_title("Top 20 Counties by Mean Bridge Risk Score (min. 50 bridges)")
    ax.legend(loc="lower right")

    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full analysis pipeline: load, score, summarise, plot."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_and_clean(INPUT_CSV)
    df = compute_risk_score(df)
    print_summary(df)

    print("-- Saving figures --")
    plot_risk_map(df, FIG1_PATH)
    plot_age_vs_condition(df, FIG2_PATH)
    plot_risk_distribution(df, FIG3_PATH)
    plot_county_risk(df, FIG4_PATH)
    print()
    print("Done.")


if __name__ == "__main__":
    main()
