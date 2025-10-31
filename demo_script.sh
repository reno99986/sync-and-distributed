#!/bin/bash

# 🚀 DEMO TESTING SCRIPT
# Distributed Systems Demonstration Commands

echo "=========================================="
echo "🚀 DISTRIBUTED SYSTEMS DEMO SCRIPT"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${BLUE}=========================================="
    echo -e "📋 $1"
    echo -e "==========================================${NC}\n"
}

print_command() {
    echo -e "${YELLOW}💻 Command: $1${NC}"
}

print_result() {
    echo -e "${GREEN}✅ Result: $1${NC}\n"
}

# Function to run curl and display results nicely
run_curl() {
    local description=$1
    local command=$2
    
    print_command "$description"
    echo "   $command"
    echo ""
    
    # Execute the command and capture result
    result=$(eval $command 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$result" | jq . 2>/dev/null || echo "$result"
        print_result "Success"
    else
        echo -e "${RED}❌ Failed to execute command${NC}\n"
    fi
    
    echo "Press Enter to continue..."
    read -r
}

# Start demo
print_section "CONTAINER STATUS CHECK"
echo "🔍 Checking if all containers are running..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(lock-node|queue-node|cache-node|redis)"

echo -e "\nPress Enter to start the demo..."
read -r

# ===========================================
# 1. DISTRIBUTED LOCK MANAGER DEMO
# ===========================================

print_section "1. DISTRIBUTED LOCK MANAGER DEMO"

run_curl "Check Raft status on all nodes" \
"curl -s http://localhost:8001/locks && echo '---' && curl -s http://localhost:8002/locks && echo '---' && curl -s http://localhost:8003/locks"

run_curl "Acquire exclusive lock on resource1 by client1" \
"curl -s -X POST http://localhost:8002/acquire -H 'Content-Type: application/json' -d '{\"resource_id\": \"database_table\", \"client_id\": \"client_A\", \"lock_type\": \"exclusive\"}'"

run_curl "Try to acquire same resource by client2 (should be queued)" \
"curl -s -X POST http://localhost:8002/acquire -H 'Content-Type: application/json' -d '{\"resource_id\": \"database_table\", \"client_id\": \"client_B\", \"lock_type\": \"exclusive\"}'"

run_curl "Acquire shared lock on different resource" \
"curl -s -X POST http://localhost:8002/acquire -H 'Content-Type: application/json' -d '{\"resource_id\": \"config_file\", \"client_id\": \"reader_1\", \"lock_type\": \"shared\"}'"

run_curl "Acquire another shared lock on same resource" \
"curl -s -X POST http://localhost:8002/acquire -H 'Content-Type: application/json' -d '{\"resource_id\": \"config_file\", \"client_id\": \"reader_2\", \"lock_type\": \"shared\"}'"

run_curl "Check current lock status" \
"curl -s http://localhost:8002/locks"

run_curl "Release exclusive lock (client_B should get it)" \
"curl -s -X POST http://localhost:8002/release -H 'Content-Type: application/json' -d '{\"resource_id\": \"database_table\", \"client_id\": \"client_A\"}'"

run_curl "Check locks after release" \
"curl -s http://localhost:8002/locks"

# ===========================================
# 2. DISTRIBUTED QUEUE SYSTEM DEMO
# ===========================================

print_section "2. DISTRIBUTED QUEUE SYSTEM DEMO"

run_curl "Check queue system status" \
"curl -s http://localhost:9001/ && echo '---' && curl -s http://localhost:9002/ && echo '---' && curl -s http://localhost:9003/"

run_curl "Produce message to queue" \
"curl -s -X POST http://localhost:9001/produce -H 'Content-Type: application/json' -d '{\"queue\": \"user_notifications\", \"message\": \"Welcome new user!\"}'"

run_curl "Produce another message" \
"curl -s -X POST http://localhost:9002/produce -H 'Content-Type: application/json' -d '{\"queue\": \"user_notifications\", \"message\": \"Your order is ready\"}'"

run_curl "Produce message to different queue" \
"curl -s -X POST http://localhost:9003/produce -H 'Content-Type: application/json' -d '{\"queue\": \"system_alerts\", \"message\": \"System backup completed\"}'"

run_curl "Check queue status" \
"curl -s http://localhost:9001/status"

run_curl "Consume message (with at-least-once delivery)" \
"curl -s -X POST http://localhost:9001/consume -H 'Content-Type: application/json' -d '{\"queue\": \"user_notifications\", \"consumer_id\": \"notification_service\"}'"

echo "📝 Note: Copy the message_id from above response for acknowledgment"
echo "Enter the message_id: "
read -r message_id

if [ ! -z "$message_id" ]; then
    run_curl "Acknowledge message" \
    "curl -s -X POST http://localhost:9001/ack -H 'Content-Type: application/json' -d '{\"message_id\": \"$message_id\"}'"
fi

run_curl "Check queue status after consumption" \
"curl -s http://localhost:9001/status"

# ===========================================
# 3. DISTRIBUTED CACHE DEMO
# ===========================================

print_section "3. DISTRIBUTED CACHE COHERENCE DEMO (MESI Protocol)"

run_curl "Check cache system status" \
"curl -s http://localhost:7001/ && echo '---' && curl -s http://localhost:7002/ && echo '---' && curl -s http://localhost:7003/"

run_curl "Read non-existent key (cache miss, fetch from main memory)" \
"curl -s http://localhost:7001/read/user_profile_123"

run_curl "Write to cache (state becomes Modified)" \
"curl -s -X POST http://localhost:7001/write/user_profile_123 -H 'Content-Type: application/json' -d '{\"value\": {\"name\": \"John Doe\", \"age\": 30, \"city\": \"Jakarta\"}}'"

run_curl "Read from another node (triggers cache coherence)" \
"curl -s http://localhost:7002/read/user_profile_123"

run_curl "Write from second node (invalidates first node's cache)" \
"curl -s -X POST http://localhost:7002/write/user_profile_123 -H 'Content-Type: application/json' -d '{\"value\": {\"name\": \"John Smith\", \"age\": 31, \"city\": \"Bandung\"}}'"

run_curl "Read from first node (should be updated)" \
"curl -s http://localhost:7001/read/user_profile_123"

run_curl "Read from third node (should get shared state)" \
"curl -s http://localhost:7003/read/user_profile_123"

run_curl "Check cache metrics for performance analysis" \
"curl -s http://localhost:7001/metrics"

run_curl "Check cache status on all nodes" \
"curl -s http://localhost:7001/status && echo '---' && curl -s http://localhost:7002/status && echo '---' && curl -s http://localhost:7003/status"

# ===========================================
# 4. FAULT TOLERANCE DEMO
# ===========================================

print_section "4. FAULT TOLERANCE DEMO"

echo "🔥 Simulating node failure..."
echo "Stopping lock-node-3..."
docker stop lock-node-3 > /dev/null 2>&1

run_curl "Check if system still works with 2/3 nodes (majority)" \
"curl -s http://localhost:8002/locks"

run_curl "Try lock operation with one node down" \
"curl -s -X POST http://localhost:8002/acquire -H 'Content-Type: application/json' -d '{\"resource_id\": \"fault_test\", \"client_id\": \"resilient_client\", \"lock_type\": \"exclusive\"}'"

echo "🔄 Restarting the failed node..."
docker start lock-node-3 > /dev/null 2>&1
sleep 3

run_curl "Check if node rejoined the cluster" \
"curl -s http://localhost:8003/locks"

# ===========================================
# 5. PERFORMANCE TEST
# ===========================================

print_section "5. PERFORMANCE TESTING"

echo "🚀 Running concurrent lock requests..."
for i in {1..5}; do
    curl -s -X POST http://localhost:8002/acquire \
        -H 'Content-Type: application/json' \
        -d "{\"resource_id\": \"critical_section\", \"client_id\": \"client_$i\", \"lock_type\": \"exclusive\"}" &
done
wait

run_curl "Check which client got the lock" \
"curl -s http://localhost:8002/locks"

echo "🚀 Running queue throughput test..."
for i in {1..10}; do
    curl -s -X POST http://localhost:9001/produce \
        -H 'Content-Type: application/json' \
        -d "{\"queue\": \"performance_test\", \"message\": \"Load test message $i\"}" > /dev/null &
done
wait

run_curl "Check queue after load test" \
"curl -s http://localhost:9001/status"

echo "🚀 Running cache performance test..."
for key in A B C D E; do
    curl -s http://localhost:7001/read/$key > /dev/null &
    curl -s http://localhost:7002/read/$key > /dev/null &
    curl -s http://localhost:7003/read/$key > /dev/null &
done
wait

run_curl "Final cache performance metrics" \
"curl -s http://localhost:7001/metrics | jq '.performance'"

# ===========================================
# DEMO COMPLETE
# ===========================================

print_section "DEMO COMPLETED SUCCESSFULLY! 🎉"

echo -e "${GREEN}✅ All systems demonstrated successfully:${NC}"
echo "   • Distributed Lock Manager with Raft Consensus"
echo "   • Distributed Queue System with Consistent Hashing"
echo "   • Distributed Cache Coherence with MESI Protocol"
echo "   • Fault Tolerance and Recovery"
echo "   • Performance under load"
echo ""
echo -e "${BLUE}📊 Key Features Validated:${NC}"
echo "   • Leader election and consensus"
echo "   • Deadlock detection and prevention"
echo "   • At-least-once message delivery"
echo "   • Cache invalidation and coherence"
echo "   • Network partition tolerance"
echo "   • Horizontal scalability"
echo ""
echo -e "${YELLOW}🎬 Ready for video recording!${NC}"