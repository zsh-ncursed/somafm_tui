#!/bin/bash

# Check for Python3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed"
    echo "Please install Python3 and try again"
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    echo "Please install pip3 and try again"
    exit 1
fi

echo "Starting somafm-tui installation..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install application
echo "Installing application..."
pip install .

# Copy completion scripts
echo "Installing completion scripts..."

# For Fish
if command -v fish &> /dev/null; then
    FISH_COMPLETIONS_DIR="$HOME/.local/share/fish/vendor_completions.d"
    mkdir -p "$FISH_COMPLETIONS_DIR"
    cp somafm.fish "$FISH_COMPLETIONS_DIR/"
    echo "Fish completion script installed in $FISH_COMPLETIONS_DIR"
fi

# For Bash
if command -v bash &> /dev/null; then
    BASH_COMPLETIONS_DIR="$HOME/.local/share/bash-completion/completions"
    mkdir -p "$BASH_COMPLETIONS_DIR"
    cp somafm.bash "$BASH_COMPLETIONS_DIR/somafm"
    echo "Bash completion script installed in $BASH_COMPLETIONS_DIR"
fi

# Create symbolic link in /usr/local/bin
echo "Creating symbolic link..."
if [ -w /usr/local/bin ]; then
    sudo ln -sf "$(pwd)/venv/bin/somafm" /usr/local/bin/somafm
    echo "Symbolic link created in /usr/local/bin"
else
    echo "Warning: Could not create symbolic link in /usr/local/bin"
    echo "You can run the application from: $(pwd)/venv/bin/somafm"
fi

echo "Installation completed!"
echo "To activate virtual environment, run: source $(pwd)/venv/bin/activate" 