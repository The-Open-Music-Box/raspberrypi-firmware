#!/bin/bash

# Enhanced SSH Key Setup Script for Raspberry Pi
# This script creates or uses existing SSH keys and configures them for passwordless access
# Compatible with bash 3.x+ (including macOS default bash)

# Enable error handling but make it compatible with older bash versions
set -e
set -u
if [[ "${BASH_VERSION%%.*}" -ge 4 ]]; then
    set -o pipefail
fi

# Colors and formatting
readonly BOLD=$(tput bold 2>/dev/null || echo "")
readonly NORMAL=$(tput sgr0 2>/dev/null || echo "")
readonly GREEN=$(tput setaf 2 2>/dev/null || echo "")
readonly RED=$(tput setaf 1 2>/dev/null || echo "")
readonly YELLOW=$(tput setaf 3 2>/dev/null || echo "")
readonly CYAN=$(tput setaf 6 2>/dev/null || echo "")
readonly BLUE=$(tput setaf 4 2>/dev/null || echo "")

# Script configuration
readonly SSH_DIR="$HOME/.ssh"
readonly SCRIPT_NAME="$(basename "$0")"

# Function to display the header
show_header() {
    echo -e "${GREEN}
    ========================================
    🎵  The Open Music Box SSH Setup  🎵
    ========================================
    ${NORMAL}"
    echo "${CYAN}${BOLD}Enhanced SSH Key Setup for Raspberry Pi${NORMAL}"
    echo ""
}

# Function to show usage
show_usage() {
    echo "${BOLD}Usage:${NORMAL}"
    echo "  $SCRIPT_NAME [OPTIONS]"
    echo ""
    echo "${BOLD}Options:${NORMAL}"
    echo "  -f, --force-override   Automatically remove conflicting SSH host keys"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "${BOLD}Examples:${NORMAL}"
    echo "  $SCRIPT_NAME               # Interactive mode with prompts"
    echo "  $SCRIPT_NAME -f            # Force override conflicting host keys"
    echo ""
    echo "${BOLD}Note:${NORMAL}"
    echo "  Use -f when you know the Raspberry Pi has been reinstalled"
    echo "  or when you get 'REMOTE HOST IDENTIFICATION HAS CHANGED' errors"
    echo ""
}

# Function to log messages
log_info() { echo "${CYAN}ℹ️  $1${NORMAL}"; }
log_success() { echo "${GREEN}✅ $1${NORMAL}"; }
log_warning() { echo "${YELLOW}⚠️️  $1${NORMAL}"; }
log_error() { echo "${RED}❌ $1${NORMAL}"; }

# Function to ask yes/no questions
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local response

    while true; do
        if [[ "$default" == "y" ]]; then
            read -p "${BLUE}$prompt [Y/n]: ${NORMAL}" response
            response="${response:-y}"
        else
            read -p "${BLUE}$prompt [y/N]: ${NORMAL}" response
            response="${response:-n}"
        fi

        case "$response" in
            [Yy]|[Yy][Ee][Ss]) return 0 ;;
            [Nn]|[Nn][Oo]) return 1 ;;
            *) echo "${RED}Please answer yes or no.${NORMAL}" ;;
        esac
    done
}

# Function to validate input
validate_input() {
    local input="$1"
    local type="$2"

    case "$type" in
        "key_name")
            if [[ ! "$input" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                log_error "Key name can only contain letters, numbers, underscores, and hyphens"
                return 1
            fi
            ;;
        "username")
            if [[ ! "$input" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                log_error "Username can only contain letters, numbers, underscores, and hyphens"
                return 1
            fi
            ;;
        "hostname")
            if [[ ! "$input" =~ ^[a-zA-Z0-9.-]+$ ]]; then
                log_error "Hostname can only contain letters, numbers, dots, and hyphens"
                return 1
            fi
            ;;
        "alias")
            if [[ ! "$input" =~ ^[a-zA-Z0-9_-]+$ ]]; then
                log_error "SSH alias can only contain letters, numbers, underscores, and hyphens"
                return 1
            fi
            ;;
    esac
    return 0
}

# Function to setup SSH directory and permissions
setup_ssh_directory() {
    log_info "Setting up SSH directory and permissions..."

    # Create SSH directory if it doesn't exist
    if [[ ! -d "$SSH_DIR" ]]; then
        mkdir -p "$SSH_DIR"
        log_success "Created SSH directory: $SSH_DIR"
    fi

    # Set correct permissions
    chmod 700 "$SSH_DIR"

    # Create or fix config file
    if [[ ! -f "$SSH_DIR/config" ]]; then
        touch "$SSH_DIR/config"
        log_success "Created SSH config file"
    fi
    chmod 600 "$SSH_DIR/config"

    log_success "SSH directory permissions configured correctly"
}

# Function to get existing SSH keys
get_existing_keys() {
    # Look for private keys (files without .pub extension that have corresponding .pub files)
    for key_file in "$SSH_DIR"/*; do
        if [[ -f "$key_file" && ! "$key_file" =~ \.pub$ && -f "${key_file}.pub" ]]; then
            echo "$key_file"
        fi
    done 2>/dev/null || true
}

# Function to select or create SSH key
select_ssh_key() {
    local existing_keys=()
    local key_file

    # Build array of existing keys (compatible with bash 3.x)
    while IFS= read -r -d '' key_file; do
        existing_keys+=("$key_file")
    done < <(get_existing_keys | tr '\n' '\0')

    # Alternative method if the above doesn't work
    if [[ ${#existing_keys[@]} -eq 0 ]]; then
        while IFS= read -r key_file; do
            [[ -n "$key_file" ]] && existing_keys+=("$key_file")
        done < <(get_existing_keys)
    fi

    if [[ ${#existing_keys[@]} -eq 0 ]]; then
        log_warning "No existing SSH key pairs found in $SSH_DIR"
        create_new_key
    else
        echo "${YELLOW}🗝️  Found existing SSH keys:${NORMAL}"
        local i=1
        for key in "${existing_keys[@]}"; do
            local key_name=$(basename "$key")
            echo "  $i) $key_name"
            ((i++))
        done
        echo "  $i) Create a new key"
        echo ""

        while true; do
            read -p "${BLUE}Choose an option (1-$i): ${NORMAL}" choice

            if [[ "$choice" =~ ^[0-9]+$ ]]; then
                if [[ "$choice" -ge 1 && "$choice" -le ${#existing_keys[@]} ]]; then
                    KEY_PATH="${existing_keys[$((choice-1))]}"
                    KEY_NAME=$(basename "$KEY_PATH")
                    log_success "Using existing key: $KEY_NAME"
                    return
                elif [[ "$choice" -eq $i ]]; then
                    create_new_key
                    return
                fi
            fi

            log_error "Invalid choice. Please enter a number between 1 and $i"
        done
    fi
}

# Function to create a new SSH key
create_new_key() {
    while true; do
        read -p "${BLUE}🆕 Name for the new SSH key (e.g., rpi_key): ${NORMAL}" KEY_NAME

        if [[ -z "$KEY_NAME" ]]; then
            log_error "Key name cannot be empty"
            continue
        fi

        if ! validate_input "$KEY_NAME" "key_name"; then
            continue
        fi

        KEY_PATH="$SSH_DIR/$KEY_NAME"

        if [[ -f "$KEY_PATH" ]]; then
            log_warning "Key '$KEY_NAME' already exists"
            if ask_yes_no "Do you want to overwrite it?"; then
                break
            else
                continue
            fi
        else
            break
        fi
    done

    log_info "Generating new SSH key pair..."

    # Generate key with proper settings
    if ssh-keygen -t ed25519 -f "$KEY_PATH" -C "$KEY_NAME-$(date +%Y%m%d)"; then
        # Set proper permissions
        chmod 600 "$KEY_PATH"
        chmod 644 "$KEY_PATH.pub"
        log_success "SSH key pair generated successfully"
    else
        log_error "Failed to generate SSH key pair"
        exit 1
    fi
}

# Function to get connection details
get_connection_details() {
    while true; do
        read -p "${BLUE}👤 Username on the Raspberry Pi (e.g., pi): ${NORMAL}" RPI_USER
        if [[ -n "$RPI_USER" ]] && validate_input "$RPI_USER" "username"; then
            break
        fi
    done

    while true; do
        read -p "${BLUE}🌐 IP address or hostname of the Raspberry Pi: ${NORMAL}" RPI_HOST
        if [[ -n "$RPI_HOST" ]] && validate_input "$RPI_HOST" "hostname"; then
            break
        fi
    done
}

# Function to test host connectivity
test_host_connectivity() {
    log_info "Testing connectivity to $RPI_HOST..."

    # Try ping first
    if ping -c 1 -W 3 "$RPI_HOST" >/dev/null 2>&1; then
        log_success "Host $RPI_HOST is reachable via ping"
        return 0
    fi

    # Try basic TCP connection to SSH port
    if timeout 5 bash -c "echo >/dev/tcp/$RPI_HOST/22" 2>/dev/null; then
        log_success "SSH service is accessible on $RPI_HOST"
        return 0
    fi

    log_error "Unable to reach $RPI_HOST"
    if ask_yes_no "Do you want to continue anyway?"; then
        return 0
    else
        exit 1
    fi
}

# Function to get SSH alias
get_ssh_alias() {
    while true; do
        read -p "${BLUE}🔖 SSH shortcut name (e.g., rpi): ${NORMAL}" SSH_ALIAS

        if [[ -z "$SSH_ALIAS" ]]; then
            log_error "SSH alias cannot be empty"
            continue
        fi

        if ! validate_input "$SSH_ALIAS" "alias"; then
            continue
        fi

        # Check if alias already exists
        if grep -q "^Host $SSH_ALIAS$" "$SSH_DIR/config" 2>/dev/null; then
            log_warning "SSH alias '$SSH_ALIAS' already exists in config"
            if ask_yes_no "Do you want to overwrite it?"; then
                # Remove existing entry
                sed -i.bak "/^Host $SSH_ALIAS$/,/^$/d" "$SSH_DIR/config"
                log_info "Removed existing entry for '$SSH_ALIAS'"
                break
            else
                continue
            fi
        else
            break
        fi
    done
}

# Function to handle host key conflicts
handle_host_key_conflict() {
    local host="$1"

    log_warning "Detected possible host key conflict for $host"

    # Check if there's an existing key in known_hosts
    if ssh-keygen -F "$host" >/dev/null 2>&1; then
        log_info "Found existing host key for $host in known_hosts"

        if ask_yes_no "Do you want to remove the old host key and accept the new one?" "y"; then
            # Remove all existing keys for this host
            ssh-keygen -R "$host" >/dev/null 2>&1

            # Also remove by IP if hostname was used
            if [[ "$host" =~ \.local$ ]] || [[ "$host" =~ ^[a-zA-Z] ]]; then
                # Try to get IP and remove it too
                local ip=$(ping -c 1 -W 1 "$host" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
                if [[ -n "$ip" ]]; then
                    ssh-keygen -R "$ip" >/dev/null 2>&1
                fi
            fi

            log_success "Removed old host key(s) for $host"
            return 0
        else
            log_error "Cannot proceed without resolving host key conflict"
            return 1
        fi
    fi

    return 0
}

# Function to copy public key to remote host
copy_public_key() {
    log_info "Copying public key to $RPI_HOST..."

    local pub_key_content
    if ! pub_key_content=$(cat "${KEY_PATH}.pub"); then
        log_error "Failed to read public key file"
        exit 1
    fi

    # Check for host key conflicts first (non-interactive test)
    local test_output
    test_output=$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o PasswordAuthentication=no "$RPI_USER@$RPI_HOST" "echo test" 2>&1 || true)

    # Check for host key verification failed
    if echo "$test_output" | grep -q "REMOTE HOST IDENTIFICATION HAS CHANGED"; then
        if ! handle_host_key_conflict "$RPI_HOST"; then
            exit 1
        fi
    fi

    # Create the command to set up authorized_keys and fix permissions
    local setup_cmd="mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$pub_key_content' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && sort ~/.ssh/authorized_keys | uniq > ~/.ssh/authorized_keys.tmp && mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys && echo 'Public key setup completed'"

    log_info "You will be prompted for your password..."

    # Use ssh-copy-id if available (more reliable)
    if command -v ssh-copy-id >/dev/null 2>&1; then
        log_info "Using ssh-copy-id to copy the key..."
        if ssh-copy-id -o StrictHostKeyChecking=accept-new -i "${KEY_PATH}" "$RPI_USER@$RPI_HOST"; then
            log_success "Public key copied successfully using ssh-copy-id"
        else
            # Fallback to manual method
            log_warning "ssh-copy-id failed, trying manual method..."
            if ssh -o StrictHostKeyChecking=accept-new "$RPI_USER@$RPI_HOST" "$setup_cmd"; then
                log_success "Public key copied and configured successfully"
            else
                log_error "Failed to copy public key"
                exit 1
            fi
        fi
    else
        # Manual method if ssh-copy-id not available
        if ssh -o StrictHostKeyChecking=accept-new "$RPI_USER@$RPI_HOST" "$setup_cmd"; then
            log_success "Public key copied and configured successfully"
        else
            log_error "Failed to copy public key"
            log_info "You may need to manually copy the key or check SSH server configuration"

            # Provide manual copy instructions
            echo ""
            log_info "Manual copy instructions:"
            echo "${CYAN}1. Copy this public key:${NORMAL}"
            echo ""
            cat "${KEY_PATH}.pub"
            echo ""
            echo "${CYAN}2. SSH into your Pi manually:${NORMAL}"
            echo "   ssh $RPI_USER@$RPI_HOST"
            echo ""
            echo "${CYAN}3. Add the key to authorized_keys:${NORMAL}"
            echo "   echo 'PASTE_KEY_HERE' >> ~/.ssh/authorized_keys"
            echo ""

            exit 1
        fi
    fi
}

# Function to update SSH config
update_ssh_config() {
    log_info "Adding entry to SSH config..."

    local config_entry="
Host $SSH_ALIAS
    HostName $RPI_HOST
    User $RPI_USER
    IdentityFile $KEY_PATH
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"

    echo "$config_entry" >> "$SSH_DIR/config"
    log_success "SSH config updated successfully"
}

# Function to fix SSH server configuration
fix_ssh_server_config() {
    log_info "Checking and fixing SSH server configuration..."

    local fix_cmd="
    # Check if we need to fix SSH config
    if ! grep -q '^PubkeyAuthentication yes' /etc/ssh/sshd_config; then
        echo 'Fixing SSH server configuration...'
        sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

        # Enable PubkeyAuthentication
        if grep -q '^#PubkeyAuthentication' /etc/ssh/sshd_config; then
            sudo sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
        elif grep -q '^PubkeyAuthentication' /etc/ssh/sshd_config; then
            sudo sed -i 's/^PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
        else
            echo 'PubkeyAuthentication yes' | sudo tee -a /etc/ssh/sshd_config
        fi

        # Ensure AuthorizedKeysFile is properly set
        if ! grep -q '^AuthorizedKeysFile' /etc/ssh/sshd_config; then
            echo 'AuthorizedKeysFile .ssh/authorized_keys' | sudo tee -a /etc/ssh/sshd_config
        fi

        # Restart SSH service
        sudo systemctl restart ssh
        echo 'SSH server configuration updated and restarted'
    else
        echo 'SSH server configuration is already correct'
    fi
    "

    if ssh -o BatchMode=no -o ConnectTimeout=10 "$RPI_USER@$RPI_HOST" "$fix_cmd"; then
        log_success "SSH server configuration checked and fixed if needed"
        return 0
    else
        log_warning "Could not automatically fix SSH server configuration"
        return 1
    fi
}
add_key_to_agent() {
    log_info "Adding key to SSH agent..."

    # Start SSH agent if not running
    if ! ssh-add -l >/dev/null 2>&1; then
        eval "$(ssh-agent -s)" >/dev/null 2>&1
    fi

    if ssh-add "$KEY_PATH" 2>/dev/null; then
        log_success "Key added to SSH agent"
    else
        log_warning "Failed to add key to SSH agent automatically"
        log_info "You can add it manually later with: ssh-add $KEY_PATH"
    fi
}

# Function to test SSH connection
test_ssh_connection() {
    log_info "Testing SSH connection..."

    # Test passwordless authentication
    if ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_ALIAS" "echo 'SSH connection test successful'" 2>/dev/null; then
        log_success "Passwordless SSH authentication working!"
        echo ""
        echo "${CYAN}${BOLD}🎉 Setup completed successfully!${NORMAL}"
        echo "${CYAN}💻 You can now connect to your Raspberry Pi with: ${BOLD}ssh $SSH_ALIAS${NORMAL}"
        echo ""

        if ask_yes_no "Would you like to connect now?"; then
            ssh "$SSH_ALIAS"
        fi
    else
        log_warning "Passwordless authentication not working yet"

        # Try to fix SSH server configuration
        if ask_yes_no "Would you like me to try fixing the SSH server configuration?"; then
            if fix_ssh_server_config; then
                log_info "Retesting SSH connection after configuration fix..."
                sleep 2

                if ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_ALIAS" "echo 'SSH connection test successful'" 2>/dev/null; then
                    log_success "Passwordless SSH authentication now working!"
                    echo ""
                    echo "${CYAN}${BOLD}🎉 Setup completed successfully!${NORMAL}"
                    echo "${CYAN}💻 You can now connect to your Raspberry Pi with: ${BOLD}ssh $SSH_ALIAS${NORMAL}"
                    echo ""

                    if ask_yes_no "Would you like to connect now?"; then
                        ssh "$SSH_ALIAS"
                    fi
                    return
                fi
            fi
        fi

        # If we get here, passwordless auth still doesn't work
        echo ""
        echo "${CYAN}🔧 Troubleshooting tips:${NORMAL}"
        echo "1. Check SSH server configuration on the Raspberry Pi"
        echo "2. Verify file permissions in ~/.ssh directory"
        echo "3. Check if SSH service is running"
        echo "4. Run: ssh -v $SSH_ALIAS to see detailed debug output"
        echo ""

        if ask_yes_no "Would you like to try connecting with password?"; then
            ssh "$SSH_ALIAS"
        fi
    fi
}

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Script exited with error code $exit_code"
    fi
}

# Main function
main() {
    # Set trap for cleanup
    trap cleanup EXIT

    # Parse command line arguments
    local force_override=false
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                show_usage
                exit 0
                ;;
            -f|--force-override)
                force_override=true
                ;;
            *)
                if [[ -n "$arg" ]]; then
                    log_error "Unknown option: $arg"
                    show_usage
                    exit 1
                fi
                ;;
        esac
    done

    # Check if running on macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        log_warning "This script is designed for macOS but may work on other Unix systems"
    fi

    # Display header
    show_header

    if [[ "$force_override" == true ]]; then
        log_info "🔧 Force override mode enabled - will automatically remove conflicting host keys"
    fi

    # Setup SSH directory
    setup_ssh_directory

    # Select or create SSH key
    select_ssh_key

    # Get connection details
    get_connection_details

    # If force override, pre-emptively remove host keys
    if [[ "$force_override" == true ]]; then
        log_info "Removing any existing host keys for $RPI_HOST..."
        ssh-keygen -R "$RPI_HOST" >/dev/null 2>&1

        # Also try to remove by IP
        local ip=$(ping -c 1 -W 1 "$RPI_HOST" 2>/dev/null | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
        if [[ -n "$ip" ]]; then
            ssh-keygen -R "$ip" >/dev/null 2>&1
        fi

        log_success "Host keys cleared"
    fi

    # Test connectivity
    test_host_connectivity

    # Get SSH alias
    get_ssh_alias

    # Copy public key
    copy_public_key

    # Update SSH config
    update_ssh_config

    # Add key to SSH agent
    add_key_to_agent

    # Test SSH connection
    test_ssh_connection

    log_success "SSH setup script completed!"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi