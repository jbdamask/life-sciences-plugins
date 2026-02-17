#!/usr/bin/env bash
# setup.sh — One-time setup for the variant-research plugin
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=== Variant Research Plugin Setup ==="
echo "Project directory: $PROJECT_DIR"

# --- Python virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV_DIR"
else
    echo "Venv already exists."
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install --quiet requests jinja2

echo "Setup complete."
echo ""
echo "Optional API keys for enhanced results:"
echo "  export NCBI_API_KEY=<your-key>          # PubMed rate limit boost"
echo "  export PATENTSVIEW_API_KEY=<your-key>   # Required for patent search"
echo "  export BIOGRID_API_KEY=<your-key>       # Required for BioGRID"
