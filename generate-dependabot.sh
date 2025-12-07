# Header
tmpfile=test
cat > "$tmpfile" <<'YAML'
version: 2
updates:
  - package-ecosystem: "docker-compose"
    directories:
YAML

# Find and sort all docker-compose.yml directories
find . -regex '.*/\(docker-\)?compose\(-[\w]+\)?\(?>\.[\w-]+\)?\.ya?ml' -print0 \
  | xargs -0 -n1 dirname \
  | sed 's|^\./||' \
  | sort \
  | while read -r dir; do
      echo "      - \"/$dir\"" >> "$tmpfile"
    done

# Append the schedule block
cat >> "$tmpfile" <<'YAML'
    schedule:
      interval: "daily"
YAML

# Install if changed
if ! [ -f .github/dependabot.yml ] || ! cmp -s "$tmpfile" .github/dependabot.yml; then
  mv "$tmpfile" .github/dependabot.yml
  echo "✅ Updated .github/dependabot.yml!"
else
  echo "ℹ️ No changes to .github/dependabot.yml."
fi
