#!/bin/bash

# Script to set up the Voiseege repository for remote pushing

echo "Setting up Voiseege repository for remote push..."

# Check if a remote repository URL was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <remote_repository_url>"
    echo "Example: $0 https://github.com/username/voiseege.git"
    exit 1
fi

REMOTE_URL=$1

# Add the remote repository
git remote add origin $REMOTE_URL

# Verify the remote was added
echo "Remote repository added:"
git remote -v

echo "Repository setup complete!"
echo ""
echo "To push the repository, use:"
echo "  git push -u origin main"