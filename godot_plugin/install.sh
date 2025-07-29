#!/bin/bash
# Installation script for the MCSR Godot Import Plugin

PLUGIN_NAME="mcsr_importer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GODOT_PROJECT_DIR="${1:-./}"

# Check if we have a target directory
if [ ! -d "$GODOT_PROJECT_DIR" ]; then
    echo "Error: Target directory '$GODOT_PROJECT_DIR' does not exist"
    echo "Usage: $0 [path_to_godot_project]"
    exit 1
fi

# Create addons directory if it doesn't exist
ADDONS_DIR="$GODOT_PROJECT_DIR/addons"
PLUGIN_DIR="$ADDONS_DIR/$PLUGIN_NAME"

mkdir -p "$PLUGIN_DIR"

# Copy plugin files
echo "Installing MCSR Import Plugin to $PLUGIN_DIR..."

cp "$SCRIPT_DIR/plugin.cfg" "$PLUGIN_DIR/"
cp "$SCRIPT_DIR/plugin.gd" "$PLUGIN_DIR/"
cp "$SCRIPT_DIR/mcsr_importer.gd" "$PLUGIN_DIR/"
cp "$SCRIPT_DIR/mcsr_material_helper.gd" "$PLUGIN_DIR/"
cp "$SCRIPT_DIR/README.md" "$PLUGIN_DIR/"

echo "Plugin installed successfully!"
echo ""
echo "To complete installation:"
echo "1. Open your Godot project"
echo "2. Go to Project Settings > Plugins"
echo "3. Enable 'Multi-Cam Sprite Renderer Import Plugin'"
echo ""
echo "The plugin will automatically handle metadata.json files when they are imported."