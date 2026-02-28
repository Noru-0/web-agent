#!/bin/bash
# Git Hook Installer for Project Context Updates
# This script sets up hooks to remind developers to update PROJECT_CONTEXT.md

HOOK_DIR=".git/hooks"
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

if [ -z "$PROJECT_ROOT" ]; then
    echo "❌ Error: This must be run from within a git repository"
    exit 1
fi

echo "🔧 Installing git hooks for PROJECT_CONTEXT.md reminders..."

# Create pre-commit hook
cat > "$PROJECT_ROOT/$HOOK_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook to remind about PROJECT_CONTEXT.md

# Check if PROJECT_CONTEXT.md exists
if [ ! -f "PROJECT_CONTEXT.md" ]; then
    exit 0
fi

# Get list of modified files
MODIFIED_FILES=$(git diff --cached --name-only --diff-filter=ACMR)

# Check if any significant files were modified (excluding PROJECT_CONTEXT.md itself)
SIGNIFICANT_CHANGES=false

for file in $MODIFIED_FILES; do
    if [[ "$file" != "PROJECT_CONTEXT.md" ]] && \
       [[ "$file" != *.md ]] && \
       [[ "$file" != .gitignore ]] && \
       [[ "$file" != LICENSE ]]; then
        SIGNIFICANT_CHANGES=true
        break
    fi
done

# If significant changes detected but PROJECT_CONTEXT.md not updated
if [ "$SIGNIFICANT_CHANGES" = true ]; then
    CONTEXT_MODIFIED=$(echo "$MODIFIED_FILES" | grep -c "PROJECT_CONTEXT.md")

    if [ "$CONTEXT_MODIFIED" -eq 0 ]; then
        echo ""
        echo "⚠️  =============================================="
        echo "⚠️  REMINDER: Update PROJECT_CONTEXT.md!"
        echo "⚠️  =============================================="
        echo ""
        echo "   You've modified code files but haven't updated"
        echo "   PROJECT_CONTEXT.md with your changes."
        echo ""
        echo "   Modified files:"
        for file in $MODIFIED_FILES; do
            if [[ "$file" != *.md ]]; then
                echo "   - $file"
            fi
        done
        echo ""
        echo "   Please update PROJECT_CONTEXT.md with:"
        echo "   1. What you changed"
        echo "   2. Why you changed it"
        echo "   3. Impact on the system"
        echo ""
        echo "   See: .agents/PROJECT_CONTEXT_UPDATE_TEMPLATE.md"
        echo ""
        read -p "   Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo ""
            echo "   Commit cancelled. Update PROJECT_CONTEXT.md and try again."
            echo ""
            exit 1
        fi
    fi
fi

exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOK_DIR/pre-commit"

# Create commit-msg hook
cat > "$PROJECT_ROOT/$HOOK_DIR/commit-msg" << 'EOF'
#!/bin/bash
# Commit-msg hook to check for PROJECT_CONTEXT.md updates

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only)

# Check if significant files were modified
SIGNIFICANT_CHANGES=false

for file in $STAGED_FILES; do
    if [[ "$file" != "PROJECT_CONTEXT.md" ]] && \
       [[ "$file" != *.md ]] && \
       [[ "$file" != .gitignore ]] && \
       [[ "$file" != LICENSE ]]; then
        SIGNIFICANT_CHANGES=true
        break
    fi
done

# Check if PROJECT_CONTEXT.md was updated
CONTEXT_UPDATED=$(echo "$STAGED_FILES" | grep -c "PROJECT_CONTEXT.md")

# If significant changes but no context update, add note to commit message
if [ "$SIGNIFICANT_CHANGES" = true ] && [ "$CONTEXT_UPDATED" -eq 0 ]; then
    # Check if commit message already has the note
    if ! grep -q "PROJECT_CONTEXT.md" "$COMMIT_MSG_FILE"; then
        echo "" >> "$COMMIT_MSG_FILE"
        echo "⚠️  Note: PROJECT_CONTEXT.md not updated in this commit" >> "$COMMIT_MSG_FILE"
    fi
fi

exit 0
EOF

chmod +x "$PROJECT_ROOT/$HOOK_DIR/commit-msg"

echo "✅ Git hooks installed successfully!"
echo ""
echo "Installed hooks:"
echo "  - pre-commit: Reminds you to update PROJECT_CONTEXT.md"
echo "  - commit-msg: Adds note if context not updated"
echo ""
echo "To bypass the reminder (not recommended):"
echo "  git commit --no-verify"
echo ""
echo "To uninstall, delete:"
echo "  .git/hooks/pre-commit"
echo "  .git/hooks/commit-msg"
echo ""
