#!/usr/bin/env bash
# =============================================================================
# bootstrap_data.sh — Full Toronto data seed for CoCivil
#
# Usage:
#   ./scripts/bootstrap_data.sh                  # full run
#   ./scripts/bootstrap_data.sh --download-only  # download open data only
#   ./scripts/bootstrap_data.sh --seed-only      # seed from existing files
#   ./scripts/bootstrap_data.sh --bbox           # dev subset (central Toronto)
#   ./scripts/bootstrap_data.sh --skip-download  # use already-downloaded files
#
# What this does:
#   1. Checks prerequisites (PostGIS, Python packages, etc.)
#   2. Downloads Toronto Open Data (parcels, zoning, dev applications)
#   3. Copies local water system data (already in repo) to the data dir
#   4. Runs alembic migrations
#   5. Seeds geospatial data (parcels → zoning → overlays → dev apps → water mains)
#   6. Seeds policy documents
#   7. Seeds reference data
#   8. Runs the audit to confirm everything looks right
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — override with environment variables if needed
# ---------------------------------------------------------------------------
PYTHON="${PYTHON:-python3}"
DATA_DIR="${DATA_DIR:-/tmp/toronto-data}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCAL_WATER_DIR="$PROJECT_ROOT/water-system-data"
VERSION_LABEL="${VERSION_LABEL:-toronto-open-data-$(date -u +%Y%m%d-%H%M%S)}"

# Flags
DOWNLOAD=true
SEED=true
USE_BBOX=false
SKIP_AUDIT=false

# Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case $arg in
    --download-only) SEED=false ;;
    --seed-only)     DOWNLOAD=false ;;
    --skip-download) DOWNLOAD=false ;;
    --bbox)          USE_BBOX=true ;;
    --skip-audit)    SKIP_AUDIT=true ;;
    --help|-h)
      sed -n '2,14p' "$0" | sed 's/^# //' | sed 's/^#//'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown argument: $arg${NC}"
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_section() {
  echo ""
  echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}${BLUE}  $1${NC}"
  echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════${NC}"
}

log_step() {
  echo -e "${CYAN}  ▶ $1${NC}"
}

log_ok() {
  echo -e "${GREEN}  ✓ $1${NC}"
}

log_warn() {
  echo -e "${YELLOW}  ⚠ $1${NC}"
}

log_error() {
  echo -e "${RED}  ✗ $1${NC}"
}

die() {
  log_error "$1"
  exit 1
}

run_py() {
  # Run a python script from the project root with the venv active
  cd "$PROJECT_ROOT"
  $PYTHON "$@"
}

check_command() {
  command -v "$1" &>/dev/null || die "$1 is not installed or not on PATH"
}

# ---------------------------------------------------------------------------
# STEP 0 — Prerequisites
# ---------------------------------------------------------------------------
log_section "STEP 0 — Checking prerequisites"

cd "$PROJECT_ROOT"

check_command "$PYTHON"
check_command "psql"

log_step "Python version"
$PYTHON --version

log_step "Checking required Python packages"
MISSING_PKGS=()
for pkg in httpx ijson ezdxf shapely pyproj geoalchemy2 sqlalchemy alembic; do
  if ! $PYTHON -c "import $pkg" &>/dev/null; then
    MISSING_PKGS+=("$pkg")
  fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
  log_warn "Missing packages: ${MISSING_PKGS[*]}"
  log_step "Installing missing packages..."
  $PYTHON -m pip install "${MISSING_PKGS[@]}" --quiet
  log_ok "Packages installed"
else
  log_ok "All required packages present"
fi

log_step "Checking database connection"
if ! $PYTHON -c "
from app.config import settings
from app.database import sync_engine
with sync_engine.connect() as conn:
    conn.execute(__import__('sqlalchemy').text('SELECT 1'))
print('  DB OK')
" 2>/dev/null; then
  die "Cannot connect to database. Check DATABASE_URL in your .env"
fi
log_ok "Database connection OK"

log_step "Checking PostGIS extension"
if ! $PYTHON -c "
from app.database import sync_engine
import sqlalchemy as sa
with sync_engine.connect() as conn:
    result = conn.execute(sa.text(\"SELECT extname FROM pg_extension WHERE extname = 'postgis'\")).fetchone()
    assert result, 'PostGIS not installed'
" 2>/dev/null; then
  log_warn "PostGIS extension not found — attempting to create it"
  $PYTHON -c "
from app.database import sync_engine
import sqlalchemy as sa
with sync_engine.begin() as conn:
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS postgis'))
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"'))
" || die "Failed to create PostGIS extension. Run as superuser or install PostGIS."
  log_ok "PostGIS extension created"
else
  log_ok "PostGIS extension present"
fi

# ---------------------------------------------------------------------------
# STEP 1 — Database migrations
# ---------------------------------------------------------------------------
log_section "STEP 1 — Running database migrations"

log_step "Running alembic upgrade head"
cd "$PROJECT_ROOT"
alembic upgrade head && log_ok "Migrations complete" || die "Alembic migration failed"

# ---------------------------------------------------------------------------
# STEP 2 — Download Toronto Open Data
# ---------------------------------------------------------------------------
if [ "$DOWNLOAD" = true ]; then
  log_section "STEP 2 — Downloading Toronto Open Data"

  mkdir -p "$DATA_DIR"
  log_step "Data directory: $DATA_DIR"

  if [ "$USE_BBOX" = true ]; then
    log_warn "BBOX mode active — central Toronto only (development subset)"
    BBOX_FLAG="--bbox"
  else
    BBOX_FLAG=""
    log_step "Mode: FULL TORONTO (production)"
  fi

  # Use our robust seed script with auto-retry on 404
  log_step "Downloading: property boundaries (~475 MB)"
  run_py -c "
import sys; sys.path.insert(0, '.')
from scripts.fix_water_mains_download import get_download_url_safe, CKAN_BASE
import httpx, pathlib, time

DATA_DIR = pathlib.Path('$DATA_DIR')
DATA_DIR.mkdir(parents=True, exist_ok=True)

downloads = [
    ('property-boundaries', 'property boundaries - 4326.geojson', 'property-boundaries-4326.geojson', 400),
    ('zoning-by-law',       'zoning area - 4326.geojson',          'zoning-area-4326.geojson',          40),
    ('zoning-by-law',       'zoning height overlay - 4326.geojson','zoning-height-overlay-4326.geojson', 10),
    ('zoning-by-law',       'zoning building setback overlay - 4326.geojson','zoning-building-setback-overlay-4326.geojson', 10),
    ('development-applications','development applications.json',   'development-applications.json',       5),
]

for pkg, match, filename, min_mb in downloads:
    dest = DATA_DIR / filename
    if dest.exists() and dest.stat().st_size > min_mb * 0.5 * 1024 * 1024:
        print(f'  SKIP {filename} ({dest.stat().st_size // (1024*1024)} MB already downloaded)')
        continue
    print(f'  Fetching URL for {pkg}...')
    url = get_download_url_safe(pkg, resource_name_match=match)
    if not url:
        print(f'  WARNING: No URL found for {pkg}, skipping')
        continue
    print(f'  Downloading {filename}...')
    start = time.monotonic()
    with httpx.stream('GET', url, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(dest, 'wb') as f:
            for chunk in r.iter_bytes(chunk_size=512*1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f'\r    {downloaded//(1024*1024)} MB / {total//(1024*1024)} MB ({pct}%)', end='', flush=True)
    print()
    size_mb = dest.stat().st_size / (1024*1024)
    elapsed = time.monotonic() - start
    print(f'  Saved {filename} ({size_mb:.0f} MB in {elapsed:.0f}s)')
"
  log_ok "Toronto Open Data downloaded"
else
  log_section "STEP 2 — Download skipped (--seed-only / --skip-download)"
fi

# ---------------------------------------------------------------------------
# STEP 3 — Stage local water system data (already in repo, no download needed)
# Maps real filenames from water-system-data/ → normalised names the
# ingestion service expects (matches WATER_LAYER_MANIFEST in water_main_ingestion.py)
# ---------------------------------------------------------------------------
log_section "STEP 3 — Staging local water system data"

mkdir -p "$DATA_DIR"

# Array of "source_filename|dest_filename|description"
declare -a WATER_FILES=(
  "Toronto Watermain 4326.geojson|water-mains-4326.geojson|Transmission water mains"
  "Watermain Distribution 4326.geojson|watermain-distribution-4326.geojson|Distribution water mains"
  "Water Hydrants Toronto.geojson|water-hydrants-4326.geojson|Water hydrants"
  "Water Valve 4326.geojson|water-valves-4326.geojson|Water valves"
  "Water Fitting 4326.geojson|water-fittings-4326.geojson|Water fittings"
  "Parks Drinking Water Sources.geojson|parks-drinking-water-4326.geojson|Parks drinking water sources"
)

for entry in "${WATER_FILES[@]}"; do
  IFS="|" read -r src_name dest_name description <<< "$entry"
  src="$LOCAL_WATER_DIR/$src_name"
  dest="$DATA_DIR/$dest_name"

  if [ -f "$dest" ]; then
    SIZE=$(du -sh "$dest" | cut -f1)
    log_ok "$description already staged ($SIZE)"
  elif [ -f "$src" ]; then
    log_step "Staging $description..."
    cp "$src" "$dest"
    SIZE=$(du -sh "$dest" | cut -f1)
    log_ok "$description staged ($SIZE)"
  else
    log_warn "$description not found — expected: water-system-data/$src_name"
  fi
done

echo ""
log_step "All staged files in $DATA_DIR:"
ls -lh "$DATA_DIR" 2>/dev/null | awk 'NR>1 {printf "    %-55s %s\n", $NF, $5}'

# ---------------------------------------------------------------------------
# STEP 4 — Apply bbox filter (dev mode only)
# ---------------------------------------------------------------------------
if [ "$USE_BBOX" = true ]; then
  log_section "STEP 4 — Applying bbox filter (dev mode)"
  run_py -c "
import sys; sys.path.insert(0, '.')
from scripts.railway_seed_full import _apply_bbox_filter
from pathlib import Path
_apply_bbox_filter(Path('$DATA_DIR'))
"
  log_ok "Bbox filter applied"
else
  log_section "STEP 4 — Bbox filter skipped (full Toronto mode)"
fi

# ---------------------------------------------------------------------------
# STEP 5 — Seed geospatial data
# ---------------------------------------------------------------------------
if [ "$SEED" = true ]; then
  log_section "STEP 5 — Seeding geospatial data"
  log_step "Version label: $VERSION_LABEL"

  run_py scripts/seed_toronto.py \
    --data-dir "$DATA_DIR" \
    --version-label "$VERSION_LABEL" \
    --jurisdiction-name "Toronto" \
    --province "Ontario" \
    --country "CA"

  log_ok "Core geospatial seed complete"

  # Water system layers — all six from local water-system-data/
  log_step "Seeding water system layers (mains, hydrants, valves, fittings, parks)..."
  run_py -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
from app.database import get_sync_db
from app.services.water_main_ingestion import seed_all_water_layers
from sqlalchemy import select
from app.models.geospatial import Jurisdiction

db = get_sync_db()
try:
    jurisdiction = db.execute(
        select(Jurisdiction).where(Jurisdiction.name == 'Toronto')
    ).scalar_one()
    results = seed_all_water_layers(
        db,
        jurisdiction_id=jurisdiction.id,
        data_dir=Path('$DATA_DIR'),
        version_label='$VERSION_LABEL',
        batch_size=1000,
    )
    print()
    for layer_type, summary in results.items():
        print(f'  {layer_type}: processed={summary[\"processed\"]:,} failed={summary[\"failed\"]} status={summary[\"status\"]}')
    db.commit()
finally:
    db.close()
"
  log_ok "Water system layers seeded"

else
  log_section "STEP 5 — Geospatial seed skipped (--download-only)"
fi

# ---------------------------------------------------------------------------
# STEP 6 — Seed policies
# ---------------------------------------------------------------------------
if [ "$SEED" = true ]; then
  log_section "STEP 6 — Seeding policy documents"
  run_py scripts/seed_policies.py \
    --jurisdiction-name "Toronto" \
    --province "Ontario" \
    --country "CA"
  log_ok "Policy documents seeded"
fi

# ---------------------------------------------------------------------------
# STEP 7 — Seed reference data
# ---------------------------------------------------------------------------
if [ "$SEED" = true ]; then
  log_section "STEP 7 — Seeding reference data"
  run_py scripts/seed_reference_data.py
  log_ok "Reference data seeded"
fi

# ---------------------------------------------------------------------------
# STEP 8 — Audit
# ---------------------------------------------------------------------------
if [ "$SEED" = true ] && [ "$SKIP_AUDIT" = false ]; then
  log_section "STEP 8 — Running audit"
  run_py scripts/audit_toronto_seed.py || log_warn "Audit completed with warnings (non-fatal)"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ALL DONE${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
if [ "$USE_BBOX" = true ]; then
  echo -e "${YELLOW}  Note: seeded with --bbox (central Toronto subset only)${NC}"
else
  echo -e "${GREEN}  Full Toronto dataset seeded.${NC}"
fi
echo -e "  Version label: ${CYAN}$VERSION_LABEL${NC}"
echo -e "  Data dir:      ${CYAN}$DATA_DIR${NC}"
echo ""