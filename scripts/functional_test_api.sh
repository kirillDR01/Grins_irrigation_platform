#!/bin/bash
# Comprehensive Functional Testing Script for Customer Management API
# Tests all endpoints as a user would experience them

set -e

BASE_URL="http://localhost:8000/api/v1"
TIMESTAMP=$(date +%s)
PASSED=0
FAILED=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASSED=$((PASSED + 1))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED=$((FAILED + 1))
}

log_test() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# ============================================================================
# CUSTOMER CRUD TESTS
# ============================================================================

log_test "TEST 1: Create Customer"
CUSTOMER_RESPONSE=$(curl -s -X POST "$BASE_URL/customers" \
  -H "Content-Type: application/json" \
  -d "{
    \"first_name\": \"Viktor\",
    \"last_name\": \"Grin\",
    \"phone\": \"612555${TIMESTAMP: -4}\",
    \"email\": \"viktor${TIMESTAMP}@grins.com\",
    \"city\": \"Eden Prairie\",
    \"notes\": \"Test customer\"
  }")

CUSTOMER_ID=$(echo "$CUSTOMER_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null)
if [ -n "$CUSTOMER_ID" ]; then
    log_pass "Created customer with ID: $CUSTOMER_ID"
else
    log_fail "Failed to create customer: $CUSTOMER_RESPONSE"
    exit 1
fi

log_test "TEST 2: Get Customer by ID"
GET_RESPONSE=$(curl -s "$BASE_URL/customers/$CUSTOMER_ID")
GET_NAME=$(echo "$GET_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('first_name', ''))" 2>/dev/null)
if [ "$GET_NAME" = "Viktor" ]; then
    log_pass "Retrieved customer: $GET_NAME"
else
    log_fail "Failed to get customer: $GET_RESPONSE"
fi

log_test "TEST 3: Update Customer"
UPDATE_RESPONSE=$(curl -s -X PUT "$BASE_URL/customers/$CUSTOMER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Viktor Updated",
    "notes": "Updated notes"
  }')
UPDATED_NAME=$(echo "$UPDATE_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('first_name', ''))" 2>/dev/null)
if [ "$UPDATED_NAME" = "Viktor Updated" ]; then
    log_pass "Updated customer name to: $UPDATED_NAME"
else
    log_fail "Failed to update customer: $UPDATE_RESPONSE"
fi

log_test "TEST 4: List Customers with Pagination"
LIST_RESPONSE=$(curl -s "$BASE_URL/customers?page=1&page_size=10")
TOTAL=$(echo "$LIST_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total', 0))" 2>/dev/null)
if [ "$TOTAL" -gt 0 ]; then
    log_pass "Listed customers, total: $TOTAL"
else
    log_fail "Failed to list customers: $LIST_RESPONSE"
fi

log_test "TEST 5: Update Customer Flags"
FLAGS_RESPONSE=$(curl -s -X PUT "$BASE_URL/customers/$CUSTOMER_ID/flags" \
  -H "Content-Type: application/json" \
  -d '{
    "is_priority": true,
    "is_red_flag": false
  }')
IS_PRIORITY=$(echo "$FLAGS_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('is_priority', False))" 2>/dev/null)
if [ "$IS_PRIORITY" = "True" ]; then
    log_pass "Updated flags - is_priority: True"
else
    log_fail "Failed to update flags: $FLAGS_RESPONSE"
fi

# ============================================================================
# CUSTOMER LOOKUP TESTS
# ============================================================================

log_test "TEST 6: Lookup by Phone"
PHONE="612555${TIMESTAMP: -4}"
LOOKUP_RESPONSE=$(curl -s "$BASE_URL/customers/lookup/phone/$PHONE")
LOOKUP_COUNT=$(echo "$LOOKUP_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)
if [ "$LOOKUP_COUNT" -gt 0 ]; then
    log_pass "Found $LOOKUP_COUNT customer(s) by phone"
else
    log_fail "Failed to lookup by phone: $LOOKUP_RESPONSE"
fi

log_test "TEST 7: Lookup by Email"
EMAIL="viktor${TIMESTAMP}@grins.com"
EMAIL_RESPONSE=$(curl -s "$BASE_URL/customers/lookup/email/$EMAIL")
EMAIL_COUNT=$(echo "$EMAIL_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)
if [ "$EMAIL_COUNT" -gt 0 ]; then
    log_pass "Found $EMAIL_COUNT customer(s) by email"
else
    log_fail "Failed to lookup by email: $EMAIL_RESPONSE"
fi

# ============================================================================
# PROPERTY TESTS
# ============================================================================

log_test "TEST 8: Add Property to Customer"
PROPERTY_RESPONSE=$(curl -s -X POST "$BASE_URL/customers/$CUSTOMER_ID/properties" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St",
    "city": "Eden Prairie",
    "state": "MN",
    "zip_code": "55344",
    "zone_count": 8,
    "system_type": "standard",
    "property_type": "residential",
    "is_primary": true
  }')
PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null)
if [ -n "$PROPERTY_ID" ]; then
    log_pass "Created property with ID: $PROPERTY_ID"
else
    log_fail "Failed to create property: $PROPERTY_RESPONSE"
fi

log_test "TEST 9: Get Property by ID"
GET_PROP_RESPONSE=$(curl -s "$BASE_URL/properties/$PROPERTY_ID")
PROP_ADDRESS=$(echo "$GET_PROP_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('address', ''))" 2>/dev/null)
if [ "$PROP_ADDRESS" = "123 Main St" ]; then
    log_pass "Retrieved property: $PROP_ADDRESS"
else
    log_fail "Failed to get property: $GET_PROP_RESPONSE"
fi

log_test "TEST 10: List Customer Properties"
LIST_PROPS_RESPONSE=$(curl -s "$BASE_URL/customers/$CUSTOMER_ID/properties")
PROPS_COUNT=$(echo "$LIST_PROPS_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)
if [ "$PROPS_COUNT" -gt 0 ]; then
    log_pass "Listed $PROPS_COUNT property(ies) for customer"
else
    log_fail "Failed to list properties: $LIST_PROPS_RESPONSE"
fi

log_test "TEST 11: Update Property"
UPDATE_PROP_RESPONSE=$(curl -s -X PUT "$BASE_URL/properties/$PROPERTY_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_count": 12,
    "access_instructions": "Gate code: 1234"
  }')
UPDATED_ZONES=$(echo "$UPDATE_PROP_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('zone_count', 0))" 2>/dev/null)
if [ "$UPDATED_ZONES" = "12" ]; then
    log_pass "Updated property zone_count to: $UPDATED_ZONES"
else
    log_fail "Failed to update property: $UPDATE_PROP_RESPONSE"
fi

log_test "TEST 12: Add Second Property"
PROPERTY2_RESPONSE=$(curl -s -X POST "$BASE_URL/customers/$CUSTOMER_ID/properties" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "456 Oak Ave",
    "city": "Plymouth",
    "state": "MN",
    "zip_code": "55441",
    "zone_count": 6,
    "system_type": "lake_pump",
    "property_type": "commercial",
    "is_primary": false
  }')
PROPERTY2_ID=$(echo "$PROPERTY2_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null)
if [ -n "$PROPERTY2_ID" ]; then
    log_pass "Created second property with ID: $PROPERTY2_ID"
else
    log_fail "Failed to create second property: $PROPERTY2_RESPONSE"
fi

log_test "TEST 13: Set Primary Property"
SET_PRIMARY_RESPONSE=$(curl -s -X PUT "$BASE_URL/properties/$PROPERTY2_ID/primary")
IS_PRIMARY=$(echo "$SET_PRIMARY_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('is_primary', False))" 2>/dev/null)
if [ "$IS_PRIMARY" = "True" ]; then
    log_pass "Set property as primary"
else
    log_fail "Failed to set primary: $SET_PRIMARY_RESPONSE"
fi

# Verify old primary was cleared
OLD_PRIMARY_RESPONSE=$(curl -s "$BASE_URL/properties/$PROPERTY_ID")
OLD_IS_PRIMARY=$(echo "$OLD_PRIMARY_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('is_primary', True))" 2>/dev/null)
if [ "$OLD_IS_PRIMARY" = "False" ]; then
    log_pass "Old primary flag was cleared"
else
    log_fail "Old primary flag was NOT cleared"
fi

# ============================================================================
# VALIDATION TESTS
# ============================================================================

log_test "TEST 14: Duplicate Phone Rejection"
DUP_RESPONSE=$(curl -s -X POST "$BASE_URL/customers" \
  -H "Content-Type: application/json" \
  -d "{
    \"first_name\": \"Duplicate\",
    \"last_name\": \"Test\",
    \"phone\": \"612555${TIMESTAMP: -4}\"
  }")
DUP_ERROR=$(echo "$DUP_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print('already exists' in str(d).lower())" 2>/dev/null)
if [ "$DUP_ERROR" = "True" ]; then
    log_pass "Duplicate phone correctly rejected"
else
    log_fail "Duplicate phone was NOT rejected: $DUP_RESPONSE"
fi

log_test "TEST 15: Invalid Zone Count Rejection"
INVALID_ZONE_RESPONSE=$(curl -s -X POST "$BASE_URL/customers/$CUSTOMER_ID/properties" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "789 Invalid St",
    "city": "Test City",
    "state": "MN",
    "zip_code": "55555",
    "zone_count": 100
  }')
ZONE_ERROR=$(echo "$INVALID_ZONE_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print('detail' in d or 'error' in str(d).lower())" 2>/dev/null)
if [ "$ZONE_ERROR" = "True" ]; then
    log_pass "Invalid zone count (100) correctly rejected"
else
    log_fail "Invalid zone count was NOT rejected: $INVALID_ZONE_RESPONSE"
fi

log_test "TEST 16: Customer Not Found (404)"
NOT_FOUND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/customers/00000000-0000-0000-0000-000000000000")
if [ "$NOT_FOUND_RESPONSE" = "404" ]; then
    log_pass "Non-existent customer returns 404"
else
    log_fail "Expected 404, got: $NOT_FOUND_RESPONSE"
fi

# ============================================================================
# SERVICE HISTORY TEST
# ============================================================================

log_test "TEST 17: Get Service History"
HISTORY_RESPONSE=$(curl -s "$BASE_URL/customers/$CUSTOMER_ID/service-history")
HISTORY_JOBS=$(echo "$HISTORY_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total_jobs', -1))" 2>/dev/null)
if [ "$HISTORY_JOBS" -ge 0 ]; then
    log_pass "Retrieved service history (total_jobs: $HISTORY_JOBS)"
else
    log_fail "Failed to get service history: $HISTORY_RESPONSE"
fi

# ============================================================================
# BULK OPERATIONS TEST
# ============================================================================

log_test "TEST 18: Bulk Update Preferences"
BULK_RESPONSE=$(curl -s -X PUT "$BASE_URL/customers/bulk/preferences" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_ids\": [\"$CUSTOMER_ID\"],
    \"sms_opt_in\": true,
    \"email_opt_in\": true
  }")
BULK_SUCCESS=$(echo "$BULK_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('updated_count', d.get('success_count', 0)))" 2>/dev/null)
if [ "$BULK_SUCCESS" -gt 0 ]; then
    log_pass "Bulk updated $BULK_SUCCESS customer(s)"
else
    log_fail "Failed bulk update: $BULK_RESPONSE"
fi

# ============================================================================
# CLEANUP - Delete Property and Customer
# ============================================================================

log_test "TEST 19: Delete Property"
DELETE_PROP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/properties/$PROPERTY2_ID")
if [ "$DELETE_PROP_STATUS" = "204" ]; then
    log_pass "Deleted property (204 No Content)"
else
    log_fail "Expected 204, got: $DELETE_PROP_STATUS"
fi

log_test "TEST 20: Soft Delete Customer"
DELETE_CUST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL/customers/$CUSTOMER_ID")
if [ "$DELETE_CUST_STATUS" = "204" ]; then
    log_pass "Soft deleted customer (204 No Content)"
else
    log_fail "Expected 204, got: $DELETE_CUST_STATUS"
fi

# Verify customer is not found after soft delete
DELETED_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/customers/$CUSTOMER_ID")
if [ "$DELETED_CHECK" = "404" ]; then
    log_pass "Deleted customer returns 404"
else
    log_fail "Deleted customer should return 404, got: $DELETED_CHECK"
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}FUNCTIONAL TEST SUMMARY${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
TOTAL=$((PASSED + FAILED))
echo -e "Total: $TOTAL"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All functional tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi
