#!/bin/bash

echo "Starting all functionality tests..."

# Check if server is running
echo "Checking server status..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:5002/v1/health -H "Authorization: Bearer test-api-key"
if [ $? -ne 0 ]; then
    echo "Error: Server is not running. Please start the server first."
    exit 1
fi

# Run all tests
echo "Running all tests..."
pytest tests/ -v

echo "All tests completed." 