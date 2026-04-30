#!/bin/bash
# Test Cost Center API Endpoints

echo "=== Cost Center API Tests ==="
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Create Cost Center
echo "1. POST /api/cost-centers - Create Sales Department"
curl -X POST "$BASE_URL/api/cost-centers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Department API Test",
    "category": "Department"
  }'
echo -e "\n"

# Test 2: List Cost Centers
echo "2. GET /api/cost-centers - List all cost centers"
curl -X GET "$BASE_URL/api/cost-centers?active_only=true"
echo -e "\n"

# Test 3: Create Allocation
echo "3. POST /api/allocations - Allocate entry to cost centers"
echo "   (Requires existing voucher/entry - see demo script)"
# curl -X POST "$BASE_URL/api/allocations" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "entry_id": 1,
#     "allocations": [
#       {"cost_center_id": 1, "amount": 50000.0, "percentage": 100.0}
#     ]
#   }'
echo -e "\n"

# Test 4: Cost Center Report
echo "4. GET /api/cost-center-report - Generate report"
curl -X GET "$BASE_URL/api/cost-center-report?id=1&from=2026-01-01&to=2026-12-31"
echo -e "\n"

echo "=== Tests Complete ==="
echo ""
echo "To test full allocation:"
echo "1. Start server: uvicorn src.tally_mac_clone.app:app --reload"
echo "2. Run demo: python3 examples/cost_center_demo.py"
echo "3. Run this script: bash examples/test_cost_center_api.sh"
