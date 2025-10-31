# 🚀 Distributed Systems Implementation



## 📋 Project Overview

This project implements a comprehensive distributed systems architecture featuring three core components:

1. **🔒 Distributed Lock Manager** - Using Raft Consensus Algorithm
2. **📮 Distributed Message Queue** - With Consistent Hashing and At-Least-Once Delivery
3. **💾 Distributed Cache System** - Implementing MESI Protocol for Cache Coherence

Built with **Python 3.11**, **asyncio**, **aiohttp**, and **Docker Compose** for full containerization.

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Lock Manager  │    │  Message Queue  │    │  Cache System   │
│   (Port 8001-3) │    │   (Port 9001-3) │    │  (Port 7001-3)  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Raft Consensus│    │ • Consistent    │    │ • MESI Protocol │
│ • Leader Election│   │   Hashing       │    │ • Bus Snooping  │
│ • Deadlock Det. │    │ • At-Least-Once │    │ • LRU Eviction  │
│ • Lock Queuing  │    │ • Redis Backend │    │ • Performance   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                               │
                    ┌─────────────────┐
                    │     Redis       │
                    │  (Port 6379)    │
                    │ Message Storage │
                    └─────────────────┘
```

---

## 🔧 System Requirements

- **Docker** & **Docker Compose**
- **Python 3.11+** (for local development)
- **Redis** (included in Docker setup)
- **aiohttp**, **asyncio** (included in requirements.txt)

---

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd TUGAS2
```

### 2. Start All Services
```bash
# Start all containers in background
docker-compose up -d

# Check container status
docker ps
```

### 3. Verify Services
```bash
# Check Lock Manager
curl http://localhost:8001/locks

# Check Queue System
curl http://localhost:9001/

# Check Cache System
curl http://localhost:7001/
```

### 4. Run Interactive Demo
```bash
# For Linux/Mac
./demo_script.sh

# For Windows
.\demo_script.ps1
```

---

## 📊 Service Details

### 🔒 **Lock Manager (Raft Consensus)**

**Ports:** 8001, 8002, 8003

**Key Features:**
- **Leader Election** with timeout-based voting
- **Distributed Consensus** following Raft algorithm
- **Deadlock Detection** and prevention
- **Lock Queuing** for concurrent requests
- **Fault Tolerance** with 2/3 majority rule

**API Endpoints:**
```bash
# Get all locks status
GET /locks

# Acquire lock
POST /acquire
{
  "resource_id": "database_table",
  "client_id": "client_A", 
  "lock_type": "exclusive"
}

# Release lock
POST /release
{
  "resource_id": "database_table",
  "client_id": "client_A"
}
```

### 📮 **Message Queue System**

**Ports:** 9001, 9002, 9003

**Key Features:**
- **Consistent Hashing** for load distribution
- **At-Least-Once Delivery** guarantee
- **Message Acknowledgment** system
- **Redis Persistence** for durability
- **Automatic Cleanup** of acknowledged messages

**API Endpoints:**
```bash
# Produce message
POST /produce
{
  "queue": "user_notifications",
  "message": "Welcome new user!"
}

# Consume message
POST /consume
{
  "queue": "user_notifications",
  "consumer_id": "notification_service"
}

# Acknowledge message
POST /ack
{
  "message_id": "uuid-message-id"
}

# Get system status
GET /status
```

### 💾 **Cache System (MESI Protocol)**

**Ports:** 7001, 7002, 7003

**Key Features:**
- **MESI Cache Coherence** (Modified, Exclusive, Shared, Invalid)
- **Bus Snooping** for inter-cache communication
- **LRU Eviction** policy
- **Performance Metrics** tracking
- **Cache Hit/Miss** statistics

**API Endpoints:**
```bash
# Read from cache
GET /read/{key}

# Write to cache
POST /write/{key}
{
  "value": {"name": "John", "age": 30}
}

# Get cache status
GET /status

# Get performance metrics
GET /metrics
```

---

## 🧪 Testing & Demo

### **Automated Demo Script**

The project includes comprehensive demo scripts for both Windows and Linux:

- **`demo_script.sh`** - Bash script for Linux/Mac
- **`demo_script.ps1`** - PowerShell script for Windows

**Demo covers:**
1. **Lock Manager**: Exclusive/shared locks, deadlock scenarios
2. **Queue System**: Message production, consumption, acknowledgment
3. **Cache Coherence**: MESI state transitions, invalidation
4. **Fault Tolerance**: Node failure simulation
5. **Performance**: Concurrent load testing

### **Manual Testing Examples**

#### Lock Manager Test:
```bash
# Terminal 1: Acquire exclusive lock
curl -X POST http://localhost:8002/acquire \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "db_table", "client_id": "client_A", "lock_type": "exclusive"}'

# Terminal 2: Try to acquire same resource (will queue)
curl -X POST http://localhost:8002/acquire \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "db_table", "client_id": "client_B", "lock_type": "exclusive"}'

# Terminal 1: Release lock (client_B gets it)
curl -X POST http://localhost:8002/release \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "db_table", "client_id": "client_A"}'
```

#### Queue System Test:
```bash
# Produce message
curl -X POST http://localhost:9001/produce \
  -H "Content-Type: application/json" \
  -d '{"queue": "orders", "message": "New order #123"}'

# Consume message
curl -X POST http://localhost:9001/consume \
  -H "Content-Type: application/json" \
  -d '{"queue": "orders", "consumer_id": "order_processor"}'

# Acknowledge message (use message_id from consume response)
curl -X POST http://localhost:9001/ack \
  -H "Content-Type: application/json" \
  -d '{"message_id": "received-message-id"}'
```

#### Cache System Test:
```bash
# Write to cache (becomes Modified state)
curl -X POST http://localhost:7001/write/user_123 \
  -H "Content-Type: application/json" \
  -d '{"value": {"name": "Alice", "score": 95}}'

# Read from another node (becomes Shared state)
curl http://localhost:7002/read/user_123

# Write from second node (invalidates first)
curl -X POST http://localhost:7002/write/user_123 \
  -H "Content-Type: application/json" \
  -d '{"value": {"name": "Alice", "score": 100}}'

# Check metrics
curl http://localhost:7001/metrics
```

---

## 🛠️ Development

### **Project Structure**
```
sync_and_distributed/
├── src/
│   ├── nodes/
│   │   ├── base_node.py      # Base node interface
│   │   ├── lock_manager.py   # Raft-based lock manager
│   │   ├── queue_node.py     # Consistent hashing queue
│   │   └── cache_node.py     # MESI cache implementation
│   ├── consensus/
│   │   └── raft.py           # Raft consensus algorithm
│   ├── communication/
│   │   ├── message_passing.py # Inter-node communication
│   │   └── failure_detection.py # Node failure detection
│   └── utils/
│       ├── config.py         # Configuration management
│       ├── hashing.py        # Consistent hashing
│       └── metrics.py        # Performance metrics
├── tests/                    # Unit and integration tests
├── docs/                     # Documentation
├── docker-compose.yaml       # Multi-service orchestration
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── README.md               # This file
```


---

## 📈 Performance Metrics

The system tracks comprehensive performance metrics:

### **Lock Manager Metrics:**
- **Leader election time**
- **Lock acquisition latency**
- **Consensus round duration**
- **Deadlock detection frequency**

### **Queue System Metrics:**
- **Message throughput** (msg/sec)
- **Average delivery latency**
- **Queue depth monitoring**
- **Consumer lag tracking**

### **Cache System Metrics:**
- **Cache hit/miss ratio**
- **State transition frequency**
- **Bus transaction overhead**
- **Memory utilization**

**Access metrics via:**
```bash
curl http://localhost:8001/metrics  # Lock Manager
curl http://localhost:9001/status   # Queue System  
curl http://localhost:7001/metrics  # Cache System
```

---

## 🔍 Troubleshooting

### **Common Issues:**

#### **Services not starting:**
```bash
# Check Docker status
docker ps -a

# View service logs
docker logs lock-node-1
docker logs queue-node-1
docker logs cache-node-1

# Restart services
docker-compose restart
```

#### **Connection refused errors:**
```bash
# Check if ports are occupied
netstat -an | grep :8001
netstat -an | grep :9001
netstat -an | grep :7001

# Clean up and restart
docker-compose down
docker system prune -f
docker-compose up -d
```

#### **Redis connection issues:**
```bash
# Check Redis status
docker logs redis

# Test Redis connectivity
docker exec -it redis redis-cli ping
```

### **Debugging Tips:**

1. **Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
docker-compose up
```

2. **Monitor resource usage:**
```bash
docker stats
```

3. **Network connectivity test:**
```bash
docker exec -it lock-node-1 ping lock-node-2
```

---

## 📚 Algorithm References

### **Raft Consensus:**
- [Raft Paper](https://raft.github.io/raft.pdf) - Original Raft consensus algorithm
- **Leader Election:** Timeout-based voting with randomized intervals
- **Log Replication:** Ensures consistency across cluster nodes

### **Consistent Hashing:**
- **Ring-based distribution** for load balancing
- **Virtual nodes** for better distribution
- **Fault tolerance** with replication factor

### **MESI Protocol:**
- **Modified (M):** Exclusive dirty state
- **Exclusive (E):** Exclusive clean state  
- **Shared (S):** Multiple readers allowed
- **Invalid (I):** Cache line not valid

---

## 🎬 Video Demonstration

 https://youtu.be/2Blqt22Ubbs

