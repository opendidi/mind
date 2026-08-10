#!/bin/bash
# ──────────────────────────────────────────────────────────────
# mind project — full quality gate
# Usage: bash scripts/run_checks.sh
# ──────────────────────────────────────────────────────────────
set -e

echo "=== Ruff Lint (Python) ==="
python -m ruff check app/ || { echo "❌ Ruff failed"; exit 1; }
echo "✅ Ruff passed"

echo ""
echo "=== Pytest ==="
pytest tests/ -v --tb=short --timeout=30 || { echo "❌ Tests failed"; exit 1; }
echo "✅ Pytest passed"

echo ""
echo "=== Frontend Type Check ==="
cd web && npx vue-tsc --noEmit || { echo "❌ Type check failed"; exit 1; }
echo "✅ Type check passed"

echo ""
echo "=== Frontend Tests (Vitest) ==="
cd web && npx vitest run || { echo "❌ Vitest failed"; exit 1; }
echo "✅ Vitest passed"

echo ""
echo "=== Frontend Build ==="
cd web && pnpm build || { echo "❌ Build failed"; exit 1; }
echo "✅ Build passed"

echo ""
echo "=== All checks passed ✅ ==="
