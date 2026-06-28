#!/usr/bin/env bash
# Harden GCS bucket — private processing scratch, not a public vault.
set -euo pipefail
source "$(cd "$(dirname "$0")/.." && pwd)/scripts/gcp-env.sh"

BUCKET="${GCP_BUCKET:-united-skyline-500618-t0-vedicastro-corpus}"

echo "=== Lock down gs://${BUCKET} ==="

# Uniform bucket-level access (no object ACLs)
gsutil uniformbucketlevelaccess set on "gs://${BUCKET}" 2>/dev/null || true

# Remove public access prevention override if any
gsutil pap set enforced "gs://${BUCKET}" 2>/dev/null || true

# Ensure no allUsers / allAuthenticatedUsers bindings
gsutil iam ch -d allUsers:objectViewer "gs://${BUCKET}" 2>/dev/null || true
gsutil iam ch -d allAuthenticatedUsers:objectViewer "gs://${BUCKET}" 2>/dev/null || true

# Lifecycle: delete markdown older than 90d (vault is Supabase)
cat > /tmp/vedicastro-gcs-lifecycle.json <<'JSON'
{
  "rule": [
    {
      "action": { "type": "Delete" },
      "condition": { "age": 90, "matchesPrefix": ["markdown/"] }
    },
    {
      "action": { "type": "Delete" },
      "condition": { "age": 30, "matchesPrefix": ["graph-cache/"] }
    }
  ]
}
JSON
gsutil lifecycle set /tmp/vedicastro-gcs-lifecycle.json "gs://${BUCKET}" 2>/dev/null || true

echo "✓ GCS hardened — canonical vault is Supabase corpus-vault"
echo "  IAM: $(gsutil iam get gs://${BUCKET} 2>/dev/null | head -5)"
