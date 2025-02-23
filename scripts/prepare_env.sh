#!/bin/bash

# Check if Poetry is installed, if not, install it
if ! command -v poetry &> /dev/null
then
    echo "Poetry not found, installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies and set up the environment
poetry install

# Activate the virtual environment
source $(poetry env info --path)/bin/activate

echo "Environment setup complete."
