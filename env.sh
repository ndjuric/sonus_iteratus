#!/bin/bash
# Create virtual environment if it doesn't exist
if [ ! -d "src/.venv" ]; then
    echo "Virtual environment not found. Creating src/.venv..."
    python3 -m venv src/.venv
    if [ $? -ne 0 ]; then
        echo "Error creating virtual environment." >&2
        exit 1
    fi
fi

# Activate the virtual environment
source src/.venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error activating virtual environment." >&2
    exit 1
fi

# Check if requirements.txt exists.
if [ -f "requirements.txt" ]; then
    # Compute hash of requirements.txt
    req_hash=$(sha256sum requirements.txt | awk '{print $1}')
    hash_file="src/.venv/requirements.sha256"
    install_reqs=false

    if [ -f "$hash_file" ]; then
        stored_hash=$(cat "$hash_file")
        if [ "$req_hash" != "$stored_hash" ]; then
            echo "Detected changes in requirements.txt. Re-installing packages..."
            install_reqs=true
        else
            echo "Requirements are up to date."
        fi
    else
        echo "No stored requirements hash found. Installing packages..."
        install_reqs=true
    fi

    if [ "$install_reqs" = true ]; then
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Error installing required packages." >&2
            exit 1
        fi
        # Update the stored hash
        echo "$req_hash" > "$hash_file"
    fi
else
    echo "requirements.txt not found. Skipping package installation."
fi

echo "Environment setup complete."