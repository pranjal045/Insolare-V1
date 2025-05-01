#!/bin/bash

# Script to install WeasyPrint dependencies on macOS using Homebrew

echo "Updating Homebrew..."
brew update

echo "Installing WeasyPrint dependencies: cairo, pango, gdk-pixbuf, libffi"
brew install cairo pango gdk-pixbuf libffi

echo "Dependencies installed. Please reinstall WeasyPrint in your virtual environment:"
echo "pip install --force-reinstall weasyprint"

echo "Installation complete."
