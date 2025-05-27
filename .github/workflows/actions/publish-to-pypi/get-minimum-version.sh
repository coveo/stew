set -e
PROJECT_NAME_AND_VERSION=$(poetry version)
VERSION_ONLY=$(echo "$PROJECT_NAME_AND_VERSION" | cut --fields 2 --delimiter ' ')
echo "$VERSION_ONLY"
