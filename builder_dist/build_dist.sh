#!/bin/bash

# UV-based build script for Linux/macOS

set -e  # Exit on error

echo "================================"
echo "Building PyQt5 App with UV"
echo "================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo "UV version: $(uv --version)"

# Install dependencies
echo ""
echo "Setting up virtual environment with UV..."
uv venv

echo ""
echo "Installing dependencies with UV..."
source .venv/bin/activate
uv sync --group dist --active

# Build executable
echo ""
echo "Building executable..."
python build_dist.py --name brillouinview --entry-point ../src/main.py

echo ""
echo "================================"
echo "Build Complete!"
echo "Executable location: dist/brillouinview"
echo "================================"
