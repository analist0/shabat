#!/bin/bash

# Script to push the Voiseege repository to remote

echo "Pushing Voiseege repository to remote..."

# Check if the origin remote exists
if ! git remote get-url origin &> /dev/null; then
    echo "Error: No remote 'origin' found."
    echo "Please set up the remote repository first using setup_remote.sh"
    exit 1
fi

# Push the repository
git push -u origin main

if [ $? -eq 0 ]; then
    echo "Repository pushed successfully!"
else
    echo "Error pushing repository. Please check your remote repository settings."
fi