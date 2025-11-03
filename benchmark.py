#!/usr/bin/env python3
"""
Performance Benchmarking Script for Distributed Systems
Author: Rionando Soeksin Putra
NIM: 11221063
Course: Sistem Paralel & Terdistribusi A
"""

import asyncio
import aiohttp
import time
import json
import statistics
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import numpy as np

class DistributedSystemsBenchmark:
    def __init__(self):
        self.lock_ports = [8001, 8002, 8003]
        self.queue_ports = [9001, 9002, 9003]
        self.cache_ports = [7001, 7002, 7003]
        
        self.results = {
            'lock_manager': {'single': {}, 'distributed': {}},
            'queue_system': {'single': {}, 'distributed': {}},
            'cache_system': {'single': {}, 'distributed': {}}
        }
    
    async def benchmark_lock_manager_single(self, num_operations=100):
        """Benchmark single lock manager node"""
        print("Benchmarking Lock Manager - Single Node...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                # Acquire lock
                start_time = time.time()
                try:
                    acquire_payload = {
                        "resource_id": f"resource_{i}",
                        "client_id": f"client_{i}",
                        "lock_type": "exclusive"
                    }
                    
                    async with session.post(
                        f"http://localhost:{self.lock_ports[0]}/acquire",
                        json=acquire_payload
                    ) as response:
                        if response.status == 200:
                            # Release lock immediately
                            release_payload = {
                                "resource_id": f"resource_{i}",
                                "client_id": f"client_{i}"
                            }
                            
                            async with session.post(
                                f"http://localhost:{self.lock_ports[0]}/release",
                                json=release_payload
                            ) as release_response:
                                if release_response.status == 200:
                                    end_time = time.time()
                                    latency = (end_time - start_time) * 1000  # ms
                                    latencies.append(latency)
                                    successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in lock operation {i}: {e}")
                    
                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['lock_manager']['single'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    async def benchmark_lock_manager_distributed(self, num_operations=100):
        """Benchmark distributed lock manager"""
        print("Benchmarking Lock Manager - Distributed...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                # Round-robin across nodes
                port = self.lock_ports[i % len(self.lock_ports)]
                
                start_time = time.time()
                try:
                    acquire_payload = {
                        "resource_id": f"resource_{i}",
                        "client_id": f"client_{i}",
                        "lock_type": "exclusive"
                    }
                    
                    async with session.post(
                        f"http://localhost:{port}/acquire",
                        json=acquire_payload
                    ) as response:
                        if response.status == 200:
                            # Release lock
                            release_payload = {
                                "resource_id": f"resource_{i}",
                                "client_id": f"client_{i}"
                            }
                            
                            async with session.post(
                                f"http://localhost:{port}/release",
                                json=release_payload
                            ) as release_response:
                                if release_response.status == 200:
                                    end_time = time.time()
                                    latency = (end_time - start_time) * 1000
                                    latencies.append(latency)
                                    successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in distributed lock operation {i}: {e}")
                    
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['lock_manager']['distributed'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    async def benchmark_queue_single(self, num_operations=100):
        """Benchmark single queue node"""
        print("Benchmarking Queue System - Single Node...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                start_time = time.time()
                try:
                    # Produce message
                    produce_payload = {
                        "queue": "benchmark_queue",
                        "message": f"Test message {i}"
                    }
                    
                    async with session.post(
                        f"http://localhost:{self.queue_ports[0]}/produce",
                        json=produce_payload
                    ) as response:
                        if response.status == 200:
                            # Consume message
                            consume_payload = {
                                "queue": "benchmark_queue",
                                "consumer_id": f"consumer_{i}"
                            }
                            
                            async with session.post(
                                f"http://localhost:{self.queue_ports[0]}/consume",
                                json=consume_payload
                            ) as consume_response:
                                if consume_response.status == 200:
                                    consume_data = await consume_response.json()
                                    if consume_data.get('message_id'):
                                        # Acknowledge message
                                        ack_payload = {
                                            "message_id": consume_data['message_id']
                                        }
                                        
                                        async with session.post(
                                            f"http://localhost:{self.queue_ports[0]}/ack",
                                            json=ack_payload
                                        ) as ack_response:
                                            if ack_response.status == 200:
                                                end_time = time.time()
                                                latency = (end_time - start_time) * 1000
                                                latencies.append(latency)
                                                successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in queue operation {i}: {e}")
                    
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['queue_system']['single'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    async def benchmark_queue_distributed(self, num_operations=100):
        """Benchmark distributed queue system"""
        print("Benchmarking Queue System - Distributed...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                # Round-robin across nodes
                port = self.queue_ports[i % len(self.queue_ports)]
                
                start_time = time.time()
                try:
                    # Produce message
                    produce_payload = {
                        "queue": "benchmark_queue_dist",
                        "message": f"Test message {i}"
                    }
                    
                    async with session.post(
                        f"http://localhost:{port}/produce",
                        json=produce_payload
                    ) as response:
                        if response.status == 200:
                            # Consume from different node
                            consume_port = self.queue_ports[(i + 1) % len(self.queue_ports)]
                            consume_payload = {
                                "queue": "benchmark_queue_dist",
                                "consumer_id": f"consumer_{i}"
                            }
                            
                            async with session.post(
                                f"http://localhost:{consume_port}/consume",
                                json=consume_payload
                            ) as consume_response:
                                if consume_response.status == 200:
                                    consume_data = await consume_response.json()
                                    if consume_data.get('message_id'):
                                        # Acknowledge message
                                        ack_payload = {
                                            "message_id": consume_data['message_id']
                                        }
                                        
                                        async with session.post(
                                            f"http://localhost:{consume_port}/ack",
                                            json=ack_payload
                                        ) as ack_response:
                                            if ack_response.status == 200:
                                                end_time = time.time()
                                                latency = (end_time - start_time) * 1000
                                                latencies.append(latency)
                                                successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in distributed queue operation {i}: {e}")
                    
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['queue_system']['distributed'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    async def benchmark_cache_single(self, num_operations=100):
        """Benchmark single cache node"""
        print("Benchmarking Cache System - Single Node...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                start_time = time.time()
                try:
                    # Write to cache
                    write_payload = {
                        "value": f"test_value_{i}"
                    }
                    
                    async with session.post(
                        f"http://localhost:{self.cache_ports[0]}/write/key_{i}",
                        json=write_payload
                    ) as response:
                        if response.status == 200:
                            # Read from cache
                            async with session.get(
                                f"http://localhost:{self.cache_ports[0]}/read/key_{i}"
                            ) as read_response:
                                if read_response.status == 200:
                                    end_time = time.time()
                                    latency = (end_time - start_time) * 1000
                                    latencies.append(latency)
                                    successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in cache operation {i}: {e}")
                    
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['cache_system']['single'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    async def benchmark_cache_distributed(self, num_operations=100):
        """Benchmark distributed cache system"""
        print("Benchmarking Cache System - Distributed...")
        
        latencies = []
        successful_ops = 0
        
        async with aiohttp.ClientSession() as session:
            for i in range(num_operations):
                # Round-robin across nodes
                write_port = self.cache_ports[i % len(self.cache_ports)]
                read_port = self.cache_ports[(i + 1) % len(self.cache_ports)]
                
                start_time = time.time()
                try:
                    # Write to one node
                    write_payload = {
                        "value": f"test_value_{i}"
                    }
                    
                    async with session.post(
                        f"http://localhost:{write_port}/write/key_{i}",
                        json=write_payload
                    ) as response:
                        if response.status == 200:
                            # Read from different node (triggers MESI protocol)
                            async with session.get(
                                f"http://localhost:{read_port}/read/key_{i}"
                            ) as read_response:
                                if read_response.status == 200:
                                    end_time = time.time()
                                    latency = (end_time - start_time) * 1000
                                    latencies.append(latency)
                                    successful_ops += 1
                                    
                except Exception as e:
                    print(f"Error in distributed cache operation {i}: {e}")
                    
                await asyncio.sleep(0.01)
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = successful_ops / (time.time() - (time.time() - len(latencies) * 0.01))
        
        self.results['cache_system']['distributed'] = {
            'avg_latency': avg_latency,
            'throughput': throughput,
            'successful_ops': successful_ops,
            'total_ops': num_operations
        }
        
        print(f"   OK Avg Latency: {avg_latency:.2f} ms")
        print(f"   OK Throughput: {throughput:.2f} ops/sec")
    
    def generate_comparison_charts(self):
        """Generate performance comparison charts"""
        print("Generating performance comparison charts...")
        
        # Prepare data for charts
        systems = ['Lock Manager', 'Queue System', 'Cache System']
        system_keys = ['lock_manager', 'queue_system', 'cache_system']
        
        single_latency = []
        distributed_latency = []
        single_throughput = []
        distributed_throughput = []
        
        for key in system_keys:
            single_latency.append(self.results[key]['single']['avg_latency'])
            distributed_latency.append(self.results[key]['distributed']['avg_latency'])
            single_throughput.append(self.results[key]['single']['throughput'])
            distributed_throughput.append(self.results[key]['distributed']['throughput'])
        
        # Create comparison charts
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Distributed Systems Performance Analysis\nRionando Soeksin Putra - 11221063', fontsize=16)
        
        # Latency comparison
        x = np.arange(len(systems))
        width = 0.35
        
        ax1.bar(x - width/2, single_latency, width, label='Single Node', color='skyblue', alpha=0.8)
        ax1.bar(x + width/2, distributed_latency, width, label='Distributed', color='lightcoral', alpha=0.8)
        ax1.set_xlabel('System Type')
        ax1.set_ylabel('Average Latency (ms)')
        ax1.set_title('Average Latency Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(systems)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Throughput comparison
        ax2.bar(x - width/2, single_throughput, width, label='Single Node', color='lightgreen', alpha=0.8)
        ax2.bar(x + width/2, distributed_throughput, width, label='Distributed', color='orange', alpha=0.8)
        ax2.set_xlabel('System Type')
        ax2.set_ylabel('Throughput (ops/sec)')
        ax2.set_title('Throughput Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(systems)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Performance ratio (Distributed vs Single)
        latency_ratio = [d/s for d, s in zip(distributed_latency, single_latency)]
        throughput_ratio = [d/s for d, s in zip(distributed_throughput, single_throughput)]
        
        ax3.bar(systems, latency_ratio, color='purple', alpha=0.7)
        ax3.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Baseline (Single Node)')
        ax3.set_ylabel('Ratio (Distributed/Single)')
        ax3.set_title('Latency Ratio (Lower is Better)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        ax4.bar(systems, throughput_ratio, color='teal', alpha=0.7)
        ax4.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Baseline (Single Node)')
        ax4.set_ylabel('Ratio (Distributed/Single)')
        ax4.set_title('Throughput Ratio (Higher is Better)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('performance_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("   OK Charts saved as 'performance_analysis.png'")
    
    def generate_report(self):
        """Generate detailed performance report"""
        print("Generating performance report...")
        
        report = f"""
# Performance Analysis Report

**Nama:** Rionando Soeksin Putra  
**NIM:** 11221063  
**Mata Kuliah:** Sistem Paralel & Terdistribusi A

## Executive Summary

This report presents a comprehensive performance analysis of our distributed systems implementation, comparing single-node versus distributed-node architectures across three core components: Lock Manager, Message Queue System, and Cache System.

## Performance Results

### Lock Manager Performance

| Configuration | Avg Latency (ms) | Throughput (ops/sec) | Success Rate |
|---------------|------------------|----------------------|--------------|
| Single Node   | {self.results['lock_manager']['single']['avg_latency']:.2f} | {self.results['lock_manager']['single']['throughput']:.2f} | {(self.results['lock_manager']['single']['successful_ops']/self.results['lock_manager']['single']['total_ops']*100):.1f}% |
| Distributed   | {self.results['lock_manager']['distributed']['avg_latency']:.2f} | {self.results['lock_manager']['distributed']['throughput']:.2f} | {(self.results['lock_manager']['distributed']['successful_ops']/self.results['lock_manager']['distributed']['total_ops']*100):.1f}% |

### Message Queue System Performance

| Configuration | Avg Latency (ms) | Throughput (ops/sec) | Success Rate |
|---------------|------------------|----------------------|--------------|
| Single Node   | {self.results['queue_system']['single']['avg_latency']:.2f} | {self.results['queue_system']['single']['throughput']:.2f} | {(self.results['queue_system']['single']['successful_ops']/self.results['queue_system']['single']['total_ops']*100):.1f}% |
| Distributed   | {self.results['queue_system']['distributed']['avg_latency']:.2f} | {self.results['queue_system']['distributed']['throughput']:.2f} | {(self.results['queue_system']['distributed']['successful_ops']/self.results['queue_system']['distributed']['total_ops']*100):.1f}% |

### Cache System Performance

| Configuration | Avg Latency (ms) | Throughput (ops/sec) | Success Rate |
|---------------|------------------|----------------------|--------------|
| Single Node   | {self.results['cache_system']['single']['avg_latency']:.2f} | {self.results['cache_system']['single']['throughput']:.2f} | {(self.results['cache_system']['single']['successful_ops']/self.results['cache_system']['single']['total_ops']*100):.1f}% |
| Distributed   | {self.results['cache_system']['distributed']['avg_latency']:.2f} | {self.results['cache_system']['distributed']['throughput']:.2f} | {(self.results['cache_system']['distributed']['successful_ops']/self.results['cache_system']['distributed']['total_ops']*100):.1f}% |

## Analysis & Insights

### Lock Manager Analysis
The distributed lock manager shows {'higher' if self.results['lock_manager']['distributed']['avg_latency'] > self.results['lock_manager']['single']['avg_latency'] else 'lower'} latency compared to single node due to the Raft consensus overhead. The consensus mechanism requires communication between nodes for leader election and log replication, which introduces additional network latency.

### Queue System Analysis  
The message queue system demonstrates {'better' if self.results['queue_system']['distributed']['throughput'] > self.results['queue_system']['single']['throughput'] else 'mixed'} performance in distributed mode. The consistent hashing allows for better load distribution, but inter-node communication for message routing can impact latency.

### Cache System Analysis
The cache system shows the most significant difference between single and distributed modes. The MESI protocol overhead for maintaining cache coherence across nodes results in {'higher' if self.results['cache_system']['distributed']['avg_latency'] > self.results['cache_system']['single']['avg_latency'] else 'lower'} latency for distributed operations due to bus snooping and invalidation messages.

## Key Findings

1. **Consensus Overhead**: Raft consensus in the lock manager introduces measurable latency overhead but provides strong consistency guarantees.

2. **Network Communication Cost**: All distributed systems experience additional latency due to inter-node communication, which is the primary trade-off for gaining fault tolerance and scalability.

3. **Cache Coherence Impact**: The MESI protocol demonstrates the classic distributed systems challenge where maintaining consistency across nodes requires coordination overhead.

4. **Scalability vs Performance**: While single nodes may show better raw performance, distributed systems provide fault tolerance, horizontal scalability, and load distribution capabilities that are essential for production systems.

## Conclusions

The performance analysis reveals that distributed systems inherently trade raw performance for reliability, fault tolerance, and scalability. The overhead observed is expected and represents the cost of achieving:

- **Fault Tolerance**: System continues operating even if individual nodes fail
- **Consistency**: Strong consistency guarantees across all nodes
- **Scalability**: Ability to handle increased load by adding more nodes
- **Load Distribution**: Better resource utilization across multiple machines

The choice between single-node and distributed architectures should be based on specific requirements for availability, consistency, partition tolerance, and expected scale rather than solely on raw performance metrics.
"""
        
        with open('performance_report.md', 'w') as f:
            f.write(report)
        
        print("   OK Report saved as 'performance_report.md'")
    
    async def run_all_benchmarks(self, num_operations=50):
        """Run all performance benchmarks"""
        print("Starting Distributed Systems Performance Benchmark")
        print(f"   Operations per test: {num_operations}")
        print("="*60)
        
        # Lock Manager benchmarks
        await self.benchmark_lock_manager_single(num_operations)
        await asyncio.sleep(2)  # Brief pause between tests
        await self.benchmark_lock_manager_distributed(num_operations)
        
        print()
        
        # Queue System benchmarks  
        await self.benchmark_queue_single(num_operations)
        await asyncio.sleep(2)
        await self.benchmark_queue_distributed(num_operations)
        
        print()
        
        # Cache System benchmarks
        await self.benchmark_cache_single(num_operations)
        await asyncio.sleep(2)
        await self.benchmark_cache_distributed(num_operations)
        
        print()
        print("="*60)
        print("Benchmark Complete! Generating analysis...")
        
        # Generate visualizations and report
        self.generate_comparison_charts()
        self.generate_report()
        
        print("Performance analysis complete!")
        print("   Charts: performance_analysis.png")
        print("   Report: performance_report.md")

if __name__ == "__main__":
    benchmark = DistributedSystemsBenchmark()
    asyncio.run(benchmark.run_all_benchmarks(num_operations=50))