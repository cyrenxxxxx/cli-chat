#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script version
VERSION="1.0.0"

# Print banner
print_banner() {
    clear
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                      Python Chat Client Setup${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}                         Version ${VERSION}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Print error message and exit
error_exit() {
    echo -e "\n${RED}ERROR: $1${NC}" >&2
    echo -e "${YELLOW}Setup failed. Please check the error above.${NC}\n"
    exit 1
}

# Print success message
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print info message
print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Print warning message
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect package manager and OS
detect_system() {
    if [ -f "/data/data/com.termux/files/usr/bin/pkg" ]; then
        PKG_MANAGER="termux"
        INSTALL_CMD="pkg install -y"
        PYTHON_PKG="python"
        PIP_CMD="pip"
        print_info "Termux environment detected"
    elif command_exists apt; then
        PKG_MANAGER="apt"
        INSTALL_CMD="apt install -y"
        PYTHON_PKG="python3"
        PIP_CMD="pip3"
        print_info "Debian/Ubuntu environment detected"
    elif command_exists pacman; then
        PKG_MANAGER="pacman"
        INSTALL_CMD="pacman -S --noconfirm"
        PYTHON_PKG="python"
        PIP_CMD="pip"
        print_info "Arch Linux environment detected"
    else
        error_exit "Unsupported system. Please install Python 3 manually."
    fi
}

# Check and install Python
check_python() {
    print_info "Checking Python installation..."
    
    if command_exists python3; then
        PYTHON_CMD="python3"
        print_success "Python 3 is installed"
    elif command_exists python; then
        PYTHON_CMD="python"
        print_success "Python is installed"
    else
        print_warning "Python not found. Installing..."
        
        if [ "$PKG_MANAGER" = "termux" ]; then
            $INSTALL_CMD python || error_exit "Failed to install Python"
        elif [ "$PKG_MANAGER" = "apt" ]; then
            sudo apt update || error_exit "Failed to update package list"
            sudo $INSTALL_CMD python3 python3-pip || error_exit "Failed to install Python"
        elif [ "$PKG_MANAGER" = "pacman" ]; then
            sudo $INSTALL_CMD python python-pip || error_exit "Failed to install Python"
        fi
        
        print_success "Python installed successfully"
    fi
    
    # Verify Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    print_info "Python version: $PYTHON_VERSION"
}

# Check and install pip
check_pip() {
    print_info "Checking pip installation..."
    
    if [ "$PKG_MANAGER" = "termux" ]; then
        if ! command_exists pip; then
            print_warning "pip not found. Installing..."
            $INSTALL_CMD python-pip || error_exit "Failed to install pip"
        fi
    elif [ "$PKG_MANAGER" = "apt" ]; then
        if ! command_exists pip3; then
            print_warning "pip3 not found. Installing..."
            sudo $INSTALL_CMD python3-pip || error_exit "Failed to install pip"
        fi
    elif [ "$PKG_MANAGER" = "pacman" ]; then
        if ! command_exists pip; then
            print_warning "pip not found. Installing..."
            sudo $INSTALL_CMD python-pip || error_exit "Failed to install pip"
        fi
    fi
    
    print_success "pip is installed"
}

# Install Python dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    if [ "$PKG_MANAGER" = "termux" ]; then
        $INSTALL_CMD clang python-dev || print_warning "Failed to install build tools"
    fi
    
    $PIP_CMD install --upgrade pip || print_warning "Failed to upgrade pip"
    $PIP_CMD install requests || error_exit "Failed to install requests"
    
    print_success "Dependencies installed successfully"
    
    # Verify installation
    $PYTHON_CMD -c "import requests" 2>/dev/null || error_exit "Failed to verify requests installation"
    print_success "Requests module verified"
}

# Download main.py
download_script() {
    print_info "Downloading chat client..."
    
    MAIN_PY_URL="https://raw.githubusercontent.com/cyrenxxxxx/cli-chat/refs/heads/main/main.py"
    SCRIPT_NAME="main.py"
    
    if command_exists curl; then
        curl -fsSL "$MAIN_PY_URL" -o "$SCRIPT_NAME" || error_exit "Failed to download using curl"
    elif command_exists wget; then
        wget -q "$MAIN_PY_URL" -O "$SCRIPT_NAME" || error_exit "Failed to download using wget"
    else
        error_exit "Neither curl nor wget found. Please install one of them."
    fi
    
    if [ -f "$SCRIPT_NAME" ]; then
        print_success "Chat client downloaded as $SCRIPT_NAME"
    else
        error_exit "Download failed: $SCRIPT_NAME not found"
    fi
}

# Create run script
create_run_script() {
    cat > run_chat.sh << 'EOF'
#!/bin/bash
# Run script for Python Chat Client

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "main.py" ]; then
    python3 main.py 2>/dev/null || python main.py
else
    echo "ERROR: main.py not found!"
    exit 1
fi
EOF
    
    chmod +x run_chat.sh
    print_success "Created run_chat.sh"
}

# Show summary
show_summary() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    Setup Complete!${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "  ${YELLOW}•${NC} Python version: ${GREEN}$PYTHON_VERSION${NC}"
    echo -e "  ${YELLOW}•${NC} Script: ${GREEN}main.py${NC}"
    echo -e "  ${YELLOW}•${NC} Run script: ${GREEN}run_chat.sh${NC}"
    echo -e "  ${YELLOW}•${NC} Dependencies: ${GREEN}requests${NC}"
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}To start the chat client:${NC}"
    echo -e "  ${YELLOW}./run_chat.sh${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

# Main function
main() {
    print_banner
    
    # Check for root/sudo requirements
    if [ "$EUID" -eq 0 ] && [ "$PKG_MANAGER" != "termux" ]; then 
        print_warning "Running as root. This is not recommended."
    fi
    
    # Detect system and setup
    detect_system
    echo ""
    
    # Check Python
    check_python
    echo ""
    
    # Check pip
    check_pip
    echo ""
    
    # Install dependencies
    install_dependencies
    echo ""
    
    # Download main script
    download_script
    echo ""
    
    # Create run script
    create_run_script
    
    # Show summary
    show_summary
}

# Trap errors
trap 'error_exit "An unexpected error occurred on line $LINENO"' ERR

# Run main function
main "$@"