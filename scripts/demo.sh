#!/bin/bash
set -e

echo "=== Zuup Forge Demo ==="
echo ""
echo "Step 1: Show the spec"
echo "---"
head -30 specs/aureon.platform.yaml
echo ""
read -p "Press Enter to compile..." || true

echo "Step 2: Compile"
echo "---"
forge compile specs/aureon.platform.yaml
echo ""

echo "Step 3: Seed with real SAM.gov data"
echo "---"
if [ -n "$SAM_GOV_API_KEY" ]; then
  python scripts/seed_sam_gov.py
else
  echo "Skipping seed (set SAM_GOV_API_KEY for real data). API will start with empty DB."
fi
echo ""

echo "Step 4: Start the API"
echo "---"
cd platforms/aureon
uvicorn app:app --port 8000 &
SERVER_PID=$!
sleep 3

echo ""
echo "Step 5: Query opportunities"
echo "---"
curl -s http://localhost:8000/api/v1/opportunities?limit=3 | python -m json.tool
echo ""

echo "Step 6: Health check"
echo "---"
curl -s http://localhost:8000/health | python -m json.tool

kill $SERVER_PID 2>/dev/null || true
cd ../..
echo ""
echo "=== Demo complete. Spec -> Running API in ~90 seconds. ==="
