#!/usr/bin/env bash
# setup.sh — One-time setup for the variant-research plugin
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENDOR_DIR="$PROJECT_DIR/vendor"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=== Variant Research Plugin Setup ==="
echo "Project directory: $PROJECT_DIR"

# --- Python virtual environment ---
echo ""
echo "--- Setting up Python virtual environment ---"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Created venv at $VENV_DIR"
else
    echo "Venv already exists at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet

echo "Installing Python dependencies..."
pip install --quiet requests jinja2

echo "Python packages installed."

# --- Vendor MCP servers ---
echo ""
echo "--- Setting up vendor MCP servers ---"
mkdir -p "$VENDOR_DIR"

# STRING-db MCP Server
if [ ! -d "$VENDOR_DIR/STRING-db-MCP-Server" ]; then
    echo "Cloning STRING-db MCP Server..."
    git clone --depth 1 https://github.com/Augmented-Nature/STRING-db-MCP-Server.git "$VENDOR_DIR/STRING-db-MCP-Server"
    cd "$VENDOR_DIR/STRING-db-MCP-Server"
    npm install --quiet
    npm run build
    cd "$PROJECT_DIR"
    echo "STRING-db MCP Server built."
else
    echo "STRING-db MCP Server already cloned."
fi

# Human Protein Atlas MCP Server
if [ ! -d "$VENDOR_DIR/ProteinAtlas-MCP-Server" ]; then
    echo "Cloning Human Protein Atlas MCP Server..."
    git clone --depth 1 https://github.com/Augmented-Nature/ProteinAtlas-MCP-Server.git "$VENDOR_DIR/ProteinAtlas-MCP-Server"
    cd "$VENDOR_DIR/ProteinAtlas-MCP-Server"
    npm install --quiet
    npm run build
    cd "$PROJECT_DIR"
    echo "HPA MCP Server built."
else
    echo "HPA MCP Server already cloned."
fi

# Google Scholar MCP Server
if [ ! -d "$VENDOR_DIR/Google-Scholar-MCP-Server" ]; then
    echo "Cloning Google Scholar MCP Server..."
    git clone --depth 1 https://github.com/JackKuo666/Google-Scholar-MCP-Server.git "$VENDOR_DIR/Google-Scholar-MCP-Server"
    cd "$VENDOR_DIR/Google-Scholar-MCP-Server"
    pip install --quiet -r requirements.txt 2>/dev/null || pip install --quiet scholarly mcp
    cd "$PROJECT_DIR"
    echo "Google Scholar MCP Server ready."
else
    echo "Google Scholar MCP Server already cloned."
fi

# GWAS Catalog MCP Server (not on PyPI, must clone + uv sync)
if [ ! -d "$VENDOR_DIR/gwas-catalog-mcp" ]; then
    echo "Cloning GWAS Catalog MCP Server..."
    git clone --depth 1 https://github.com/koido/gwas-catalog-mcp.git "$VENDOR_DIR/gwas-catalog-mcp"
    cd "$VENDOR_DIR/gwas-catalog-mcp"
    uv sync
    cd "$PROJECT_DIR"
    echo "GWAS Catalog MCP Server ready."
else
    echo "GWAS Catalog MCP Server already cloned."
fi

# --- Create reports directory ---
mkdir -p "$PROJECT_DIR/reports"

# --- Verify uvx-based servers are accessible ---
echo ""
echo "--- Verifying uvx-based MCP servers ---"
for pkg in patent-mcp-server opentargets-mcp; do
    if uvx --help >/dev/null 2>&1; then
        echo "  uvx available for: $pkg (will be fetched on first use)"
    fi
done
echo "  BioMCP: uvx --from biomcp-python biomcp run"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Optional: Set these environment variables for enhanced access:"
echo "  export NCBI_API_KEY=<your-key>        # PubMed rate limit boost"
echo "  export PATENTSVIEW_API_KEY=<your-key>   # Full PatentsView access"
echo "  export BIOGRID_API_KEY=<your-key>      # Required for BioGRID"
