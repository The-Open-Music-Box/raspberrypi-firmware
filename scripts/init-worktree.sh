#!/bin/bash
# Initialize worktree dependencies for TheOpenMusicBox

set -e

WORKTREE_DIR="$1"

if [ -z "$WORKTREE_DIR" ]; then
    echo "Usage: $0 <worktree-directory>"
    exit 1
fi

if [ ! -d "$WORKTREE_DIR" ]; then
    echo "Error: Worktree directory does not exist: $WORKTREE_DIR"
    exit 1
fi

echo "🔧 Initializing worktree: $WORKTREE_DIR"
cd "$WORKTREE_DIR"

# Initialize submodules
echo "📦 Initializing submodules..."
git submodule init
git submodule update

# Checkout release branch for contracts (contains generated TypeScript types)
echo "🔄 Checking out contracts release branch..."
cd contracts
git checkout release
cd ..
echo "✅ Contracts submodule on release branch"

# Link Python venv from main repo (saves space and time)
if [ ! -e "back/venv" ]; then
    echo "🐍 Linking Python venv..."
    MAIN_REPO_PATH=$(git worktree list | head -1 | awk '{print $1}')
    if [ -d "$MAIN_REPO_PATH/back/venv" ]; then
        ln -s "$MAIN_REPO_PATH/back/venv" "back/venv"
        echo "✅ Python venv linked from main repo"
    else
        echo "⚠️  No venv found in main repo - run 'cd back && python -m venv venv && pip install -r requirements.txt'"
    fi
fi

# Frontend dependencies - Option A: Link node_modules (faster, saves space)
if [ ! -e "front/node_modules" ]; then
    echo "📦 Checking frontend dependencies..."
    MAIN_REPO_PATH=$(git worktree list | head -1 | awk '{print $1}')

    if [ -d "$MAIN_REPO_PATH/front/node_modules" ]; then
        echo "🔗 Linking node_modules from main repo (saves 1.6GB)..."
        ln -s "$MAIN_REPO_PATH/front/node_modules" "front/node_modules"
        echo "✅ Frontend node_modules linked"
    else
        echo "📦 Installing frontend dependencies (this will take a few minutes)..."
        cd front && npm install && cd ..
    fi
fi

echo ""
echo "✅ Worktree initialized successfully!"
echo ""
echo "You can now run:"
echo "  cd $WORKTREE_DIR"
echo "  ./deploy.sh --test-only"