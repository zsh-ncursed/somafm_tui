#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

# Function to check Python version
check_python_version() {
    local version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if (( $(echo "$version < 3.7" | bc -l) )); then
        print_error "Python 3.7 or higher is required. Current version: $version"
        return 1
    fi
    return 0
}

# Function to install system dependencies
install_system_deps() {
    print_message "Installing system dependencies..."
    
    if command -v pacman &> /dev/null; then
        # Arch Linux
        sudo pacman -S --needed mpv python python-pip cava
    elif command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y mpv python3 python3-pip cava
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y mpv python3 python3-pip cava
    else
        print_warning "Could not determine package manager. Please install MPV and CAVA manually."
        return 1
    fi
    
    return 0
}

# Main installation process
main() {
    print_message "Starting SomaFM TUI installation..."
    
    # Check Python
    if ! check_command python3; then
        print_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check Python version
    if ! check_python_version; then
        exit 1
    fi
    
    # Check pip
    if ! check_command pip3; then
        print_error "pip3 is required but not found"
        exit 1
    fi
    
    # Check MPV
    if ! check_command mpv; then
        print_warning "MPV not found. Attempting to install..."
        if ! install_system_deps; then
            print_error "Failed to install MPV. Please install it manually."
            exit 1
        fi
    fi
    
    # Check CAVA (for visualization)
    if ! check_command cava; then
        print_warning "CAVA not found (optional, for audio visualization). Attempting to install..."
        if ! install_system_deps; then # This will attempt to install mpv again if it was also missing, which is okay.
            print_warning "Failed to install CAVA. Please install it manually if you want audio visualization."
        else
            if ! check_command cava; then # Check again after install attempt
                print_warning "CAVA still not found after install attempt. Please install it manually for visualization."
            else
                print_message "CAVA successfully installed."
            fi
        fi
    else
        print_message "CAVA found."
    fi
    
    # Create virtual environment
    print_message "Creating virtual environment..."
    if ! python3 -m venv venv; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_message "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_message "Installing Python dependencies..."
    if ! pip install -r requirements.txt; then
        print_error "Failed to install Python dependencies"
        exit 1
    fi
    
    # Install application
    print_message "Installing application..."
    if ! pip install .; then
        print_error "Failed to install application"
        exit 1
    fi
    
    # Install completion scripts
    print_message "Installing completion scripts..."
    
    # For Fish
    if command -v fish &> /dev/null; then
        FISH_COMPLETIONS_DIR="$HOME/.local/share/fish/vendor_completions.d"
        mkdir -p "$FISH_COMPLETIONS_DIR"
        if cp somafm.fish "$FISH_COMPLETIONS_DIR/"; then
            print_message "Fish completion script installed in $FISH_COMPLETIONS_DIR"
        else
            print_warning "Failed to install Fish completion script"
        fi
    fi
    
    # For Bash
    if command -v bash &> /dev/null; then
        BASH_COMPLETIONS_DIR="$HOME/.local/share/bash-completion/completions"
        mkdir -p "$BASH_COMPLETIONS_DIR"
        if cp somafm.bash "$BASH_COMPLETIONS_DIR/somafm"; then
            print_message "Bash completion script installed in $BASH_COMPLETIONS_DIR"
        else
            print_warning "Failed to install Bash completion script"
        fi
    fi
    
    # Create symbolic link
    print_message "Creating symbolic link..."
    if [ -w /usr/local/bin ]; then
        if sudo ln -sf "$(pwd)/venv/bin/somafm" /usr/local/bin/somafm; then
            print_message "Symbolic link created in /usr/local/bin"
        else
            print_warning "Failed to create symbolic link in /usr/local/bin"
        fi
    else
        print_warning "Could not create symbolic link in /usr/local/bin"
        print_message "You can run the application from: $(pwd)/venv/bin/somafm"
    fi
    
    print_message "Installation completed successfully!"
    print_message "To activate virtual environment, run: source $(pwd)/venv/bin/activate"
    print_message "To run the application, type: somafm"
}

# Run main function
main 