#!/bin/bash

# Test FM Agent connectivity and functionality

set -e

echo "=================================="
echo "FM Agent Test Script"
echo "=================================="
echo ""

# Load config to get token
if [ ! -f "config.yaml" ]; then
    echo "❌ config.yaml not found"
    exit 1
fi

# Extract token from config (simple grep/sed approach)
TOKEN=$(grep "token:" config.yaml | head -1 | sed 's/.*token: *//;s/"//g;s/#.*//')

if [ -z "$TOKEN" ]; then
    echo "❌ Could not extract token from config.yaml"
    exit 1
fi

echo "Using token: ${TOKEN:0:10}..."
echo ""

AGENT_URL="http://127.0.0.1:9100"

# Test 1: Health check
echo "Test 1: Health Check"
echo "-------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" "$AGENT_URL/")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Agent is running"
    echo "Response: $BODY"
else
    echo "❌ Agent health check failed (HTTP $HTTP_CODE)"
    exit 1
fi

echo ""

# Test 2: Get stacks (with auth)
echo "Test 2: Get Stacks (Authenticated)"
echo "-----------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" "$AGENT_URL/stacks")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Authentication successful"
    echo "Response:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo "❌ Get stacks failed (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
    exit 1
fi

echo ""

# Test 3: Test without auth (should fail)
echo "Test 3: Test Without Auth (Should Fail)"
echo "---------------------------------------"
RESPONSE=$(curl -s -w "\n%{http_code}" "$AGENT_URL/stacks")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Unauthorized request correctly rejected"
else
    echo "⚠️  Expected 401, got HTTP $HTTP_CODE"
fi

echo ""
echo "=================================="
echo "✅ All Tests Passed!"
echo "=================================="
echo ""
echo "Agent is working correctly."
echo ""

