#!/bin/bash
# TuxSec Release Script
# Handles version bumping, migrations, changelog updates, and git operations

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default bump type
BUMP_TYPE="${1:-patch}"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    print_error "Invalid bump type: $BUMP_TYPE"
    echo "Usage: $0 [major|minor|patch]"
    echo "  major - Increment major version (X.0.0)"
    echo "  minor - Increment minor version (0.X.0)"
    echo "  patch - Increment patch version (0.0.X) [default]"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "tuxsec-agent.spec" ]; then
    print_error "tuxsec-agent.spec not found. Please run this script from the project root."
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes:"
    git status --short
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Aborted by user"
        exit 1
    fi
fi

# Get current version from spec file
CURRENT_VERSION=$(grep "^Version:" tuxsec-agent.spec | awk '{print $2}' | tr -d ' ')
print_info "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

# Bump version based on type
case "$BUMP_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
print_info "New version: $NEW_VERSION"

# Confirm with user
read -p "Proceed with release $NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Aborted by user"
    exit 1
fi

echo
print_info "Starting release process..."
echo

# Step 1: Update version in spec file
print_info "Updating version in tuxsec-agent.spec..."
sed -i "s/^Version:.*/Version:        $NEW_VERSION/" tuxsec-agent.spec
print_success "Updated tuxsec-agent.spec"

# Step 2: Update version in setup.py
if [ -f "setup.py" ]; then
    print_info "Updating version in setup.py..."
    sed -i "s/version='[^']*'/version='$NEW_VERSION'/" setup.py
    print_success "Updated setup.py"
fi

# Step 3: Update version in agent/__init__.py
print_info "Creating agent/__init__.py with version..."
cat > agent/__init__.py <<EOF
"""
TuxSec Agent - Secure firewall management agent
"""

__version__ = "$NEW_VERSION"
__author__ = "TuxSec Team"
__license__ = "MIT"
EOF
print_success "Updated agent/__init__.py"

# Step 4: Run Django migrations
if [ -d "web_ui" ]; then
    print_info "Running Django migrations..."
    cd web_ui
    
    # Check if virtual environment exists
    if [ -f "../.venv/bin/python" ]; then
        PYTHON="../.venv/bin/python"
    elif [ -f ".venv/bin/python" ]; then
        PYTHON=".venv/bin/python"
    else
        PYTHON="python3"
    fi
    
    # Make migrations
    print_info "Creating new migrations..."
    $PYTHON manage.py makemigrations
    
    # Check if any migrations were created
    if git diff --name-only | grep -q "migrations/"; then
        print_success "New migrations created"
    else
        print_info "No new migrations needed"
    fi
    
    # Apply migrations to check they work
    print_info "Testing migrations..."
    $PYTHON manage.py migrate
    print_success "Migrations applied successfully"
    
    cd ..
fi

# Step 5: Update CHANGELOG.md
print_info "Updating CHANGELOG.md..."
TODAY=$(date +%Y-%m-%d)

# Create a temporary file with the new entry
cat > /tmp/changelog_entry.md <<EOF
## [$NEW_VERSION] - $TODAY

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

EOF

# Insert the new entry after the [Unreleased] section
if grep -q "## \[Unreleased\]" CHANGELOG.md; then
    # Create temporary file
    awk -v entry="$(cat /tmp/changelog_entry.md)" '
        /## \[Unreleased\]/ {
            print
            print ""
            print entry
            next
        }
        {print}
    ' CHANGELOG.md > /tmp/changelog_new.md
    mv /tmp/changelog_new.md CHANGELOG.md
    print_success "Updated CHANGELOG.md"
else
    print_warning "Could not find [Unreleased] section in CHANGELOG.md"
fi

# Update the version links at the bottom
if grep -q "\[Unreleased\]:" CHANGELOG.md; then
    # Update the Unreleased link to compare against new version
    sed -i "s|\[Unreleased\]:.*|\[Unreleased\]: https://github.com/MrMEEE/tuxsec/compare/v$NEW_VERSION...HEAD|" CHANGELOG.md
    
    # Add new version link if it doesn't exist
    if ! grep -q "\[$NEW_VERSION\]:" CHANGELOG.md; then
        # Find the line with [Unreleased] and add new version link after it
        sed -i "/\[Unreleased\]:/a [$NEW_VERSION]: https://github.com/MrMEEE/tuxsec/releases/tag/v$NEW_VERSION" CHANGELOG.md
    fi
fi

rm -f /tmp/changelog_entry.md

print_warning "Please edit CHANGELOG.md to add release notes for version $NEW_VERSION"
read -p "Press Enter when you've updated the CHANGELOG..."

# Step 6: Build and test
print_info "Building RPMs to verify everything works..."
if make rpm > /tmp/tuxsec-build.log 2>&1; then
    print_success "RPM build successful"
    rm -f /tmp/tuxsec-build.log
else
    print_error "RPM build failed! Check /tmp/tuxsec-build.log"
    exit 1
fi

# Step 7: Git operations
print_info "Staging changes..."
git add -A

print_info "Creating commit..."
git commit -m "Release version $NEW_VERSION

- Updated version to $NEW_VERSION in spec file and setup.py
- Created/updated Django migrations
- Updated CHANGELOG.md
"
print_success "Committed changes"

print_info "Creating git tag v$NEW_VERSION..."
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"
print_success "Created tag v$NEW_VERSION"

# Step 8: Push to remote
print_info "Pushing to remote repository..."
read -p "Push changes and tag to origin? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git push origin main
    print_success "Pushed changes to main branch"
    
    git push origin "v$NEW_VERSION"
    print_success "Pushed tag v$NEW_VERSION"
    
    echo
    print_success "Release $NEW_VERSION completed successfully!"
    echo
    print_info "GitHub Actions will now build RPMs for RHEL 9 and RHEL 10"
    print_info "Check the progress at: https://github.com/MrMEEE/tuxsec/actions"
    echo
else
    print_warning "Changes and tag not pushed to remote"
    print_info "You can push manually with:"
    echo "  git push origin main"
    echo "  git push origin v$NEW_VERSION"
fi

# Step 9: Summary
echo
print_success "=========================================="
print_success "Release Summary"
print_success "=========================================="
echo "Version:      $CURRENT_VERSION → $NEW_VERSION"
echo "Bump Type:    $BUMP_TYPE"
echo "Tag:          v$NEW_VERSION"
echo "Branch:       main"
echo "Date:         $TODAY"
print_success "=========================================="
echo
