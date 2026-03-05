#!/bin/bash
# =============================================================================
# RTSP Live Processing Test Script
# =============================================================================
# This script tests the RTSP live processing feature for STEAD anomaly detection.
#
# Workflow:
# 1. Input RTSP URL (or video file) → STEAD inference → Annotated MP4 Output → FFmpeg Streaming
#
# Since we don't have a test RTSP URL, this script uses a local video file
# simulated as an RTSP stream.
# =============================================================================

set -e

# Configuration
BASE_URL="http://localhost:8000"
TOKEN=""  # Set your auth token here

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}RTSP Live Processing Test Script${NC}"
echo -e "${YELLOW}========================================${NC}"

# Check if token is set
if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: Please set your auth token in the script${NC}"
    echo "You can get a token by logging in:"
    echo "  curl -X POST ${BASE_URL}/api/auth/login/ -H 'Content-Type: application/json' -d '{\"email\": \"your@email.com\", \"password\": \"yourpassword\"}'"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# =============================================================================
# Test 1: Check Model Status
# =============================================================================
echo -e "\n${GREEN}1. Checking STEAD model status...${NC}"
curl -s -X GET "${BASE_URL}/api/stead/status/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" | python3 -m json.tool

# =============================================================================
# Test 2: Check FFmpeg Status
# =============================================================================
echo -e "\n${GREEN}2. Checking FFmpeg status...${NC}"
curl -s -X GET "${BASE_URL}/api/stead/ffmpeg/status/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" | python3 -m json.tool

# =============================================================================
# Test 3: Start RTSP Live Processing with Test Video
# =============================================================================
echo -e "\n${GREEN}3. Starting RTSP live processing with test video...${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/stead/rtsp/test/simulate/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d '{
        "fps": 15,
        "threshold": 0.7,
        "max_duration": 60
    }')

echo "$RESPONSE" | python3 -m json.tool

# Extract job_id from response
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}Failed to start job. Check the response above.${NC}"
    exit 1
fi

echo -e "\n${GREEN}Job started with ID: $JOB_ID${NC}"

# =============================================================================
# Test 4: Check Job Status (poll every 5 seconds)
# =============================================================================
echo -e "\n${GREEN}4. Checking job status...${NC}"
for i in {1..12}; do
    echo -e "\n${YELLOW}Status check $i/12...${NC}"
    STATUS_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/status/" \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json")
    
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    
    # Check if job is still running
    IS_RUNNING=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_running', True))")
    
    if [ "$IS_RUNNING" = "False" ]; then
        echo -e "${GREEN}Job completed!${NC}"
        break
    fi
    
    sleep 5
done

# =============================================================================
# Test 5: Stop Job and Get Results
# =============================================================================
echo -e "\n${GREEN}5. Stopping job and getting results...${NC}"
STOP_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/stop/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json")

echo "$STOP_RESPONSE" | python3 -m json.tool

# =============================================================================
# Test 6: List All Live Jobs
# =============================================================================
echo -e "\n${GREEN}6. Listing all live processing jobs...${NC}"
curl -s -X GET "${BASE_URL}/api/stead/rtsp/live/" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" | python3 -m json.tool

# =============================================================================
# Test 7: Get Streaming URLs
# =============================================================================
echo -e "\n${GREEN}7. Streaming URLs:${NC}"
echo "Direct stream: ${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/stream/"
echo "HLS playlist: ${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/hls/"

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}Test Complete!${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "\nTo stream the output video in a browser, use:"
echo "  curl -O ${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/stream/"
echo -e "\nOr play with VLC:"
echo "  vlc ${BASE_URL}/api/stead/rtsp/live/${JOB_ID}/stream/"
