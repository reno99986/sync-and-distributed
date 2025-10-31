# src/nodes/cache_node.py

import asyncio
import os  # <-- TAMBAHKAN
import logging
import time
from aiohttp import web
from collections import OrderedDict # Penting untuk LRU

# Impor utilitas komunikasi kita yang sudah di-update
from src.communication.message_passing import send_message

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# Kapasitas cache (misal: hanya 5 item) untuk menguji LRU
CACHE_CAPACITY = 5

class CacheNode:
    
    # --- UBAH FUNGSI __init__ ---
    def __init__(self, host: str, port: int, node_id: str, peer_names: list, peer_port: int):
        self.host = host
        self.port = port
        self.node_id = node_id
        self.peer_urls = {}
        
        for p_name in peer_names:
            self.peer_urls[p_name] = f"http://{p_name}:{peer_port}"

        # --- Data Inti Node ---
        
        # 1. Cache Lokal (LRU): Menyimpan data (key -> value)
        #    OrderedDict akan melacak urutan item diakses
        self.cache = OrderedDict()
        
        # 2. State Cache: Menyimpan state MESI (key -> "M", "E", "S", atau "I")
        self.cache_state = {}
        
        # 3. Simulasi Memori Utama (DRAM)
        #    Ini adalah "sumber kebenaran"
        self.simulated_main_memory = {
            "X": 10,
            "Y": 20,
            "Z": 30,
            "A": 40,
            "B": 50,
            "C": 60
        }
        
        # 4. Performance Metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "read_requests": 0,
            "write_requests": 0,
            "invalidations_sent": 0,
            "invalidations_received": 0,
            "bus_transactions": 0,
            "start_time": time.time()
        }
        
        log.info(f"Cache Node {self.node_id} dibuat. Peers: {list(self.peer_urls.keys())}")

    # --- Fungsi Helper ---

    async def broadcast_bus_message(self, endpoint: str, payload: dict):
        """Mengirim pesan ke semua node lain di bus dan mengumpulkan balasan."""
        self.metrics["bus_transactions"] += 1
        tasks = []
        for peer_url in self.peer_urls.values():
            tasks.append(send_message(f"{peer_url}{endpoint}", payload))
        
        # Jalankan semua secara paralel dan kumpulkan hasilnya
        responses = await asyncio.gather(*tasks)
        return responses

    def update_cache(self, key: str, value, new_state: str):
        """Helper untuk update cache, state, dan me-manage LRU."""
        log.info(f"[{self.node_id}] UPDATE: '{key}' = {value}, State = {new_state}")
        self.cache[key] = value
        self.cache_state[key] = new_state
        # Tandai sebagai 'baru saja diakses' (pindahkan ke akhir dict)
        self.cache.move_to_end(key)
        
        # Logic LRU: Jika cache penuh, keluarkan yang paling lama
        if len(self.cache) > CACHE_CAPACITY:
            # popitem(last=False) menghapus item PERTAMA (paling lama)
            oldest_key, oldest_value = self.cache.popitem(last=False)
            del self.cache_state[oldest_key]
            log.warning(f"[{self.node_id}] LRU Evicted: '{oldest_key}'")

    # --- 1. Endpoint untuk "CPU" Lokal (Client Request) ---

    async def handle_local_read(self, request: web.Request):
        """
        Handler untuk: GET /read/{key}
        CPU di node ini meminta data.
        """
        start_time = time.time()
        self.metrics["read_requests"] += 1
        
        key = request.match_info.get('key')
        state = self.cache_state.get(key, "I") # Default "Invalid" jika tidak ada
        
        # CASE 1: READ HIT (Kita punya data yang valid)
        if key in self.cache and state != "I":
            self.metrics["cache_hits"] += 1
            log.info(f"[{self.node_id}] READ HIT: '{key}', State: {state}")
            value = self.cache[key]
            # Tandai sebagai baru diakses (untuk LRU)
            self.cache.move_to_end(key)
            response_time = (time.time() - start_time) * 1000  # ms
            return web.json_response({
                "key": key, 
                "value": value, 
                "state": state,
                "response_time_ms": round(response_time, 2)
            })

        # CASE 2: READ MISS (Kita tidak punya, atau datanya Invalid)
        self.metrics["cache_misses"] += 1
        log.warning(f"[{self.node_id}] READ MISS: '{key}'")
        
        # Kirim "Bus Read" ke semua node lain
        payload = {"key": key}
        responses = await self.broadcast_bus_message(f"/bus/read_miss/{key}", payload)
        
        data_found_on_bus = None
        is_shared = False
        
        for r in responses:
            # Cek jika 'r' tidak None dan punya 'state'
            if r and r.get("state") in ("M", "E", "S"):
                data_found_on_bus = r.get("data")
                is_shared = True # Jika ada yang punya, itu jadi "Shared"
                break # Cukup temukan satu
        
        response_time = (time.time() - start_time) * 1000  # ms
        
        if data_found_on_bus is not None:
            # Data ditemukan di cache lain
            log.info(f"[{self.node_id}] Data '{key}' didapat dari cache peer.")
            self.update_cache(key, data_found_on_bus, "S") # State kita jadi Shared
            return web.json_response({
                "key": key, 
                "value": data_found_on_bus, 
                "state": "S",
                "response_time_ms": round(response_time, 2)
            })
        else:
            # Data tidak ada di cache lain, ambil dari memori utama
            log.info(f"[{self.node_id}] Data '{key}' didapat dari Main Memory.")
            value = self.simulated_main_memory.get(key)
            # Kita satu-satunya yang punya, jadi state "Exclusive"
            self.update_cache(key, value, "E") 
            return web.json_response({
                "key": key, 
                "value": value, 
                "state": "E",
                "response_time_ms": round(response_time, 2)
            })

    async def handle_local_write(self, request: web.Request):
        """
        Handler untuk: POST /write/{key}
        Body: {"value": X}
        CPU di node ini ingin menulis data.
        """
        start_time = time.time()
        self.metrics["write_requests"] += 1
        
        key = request.match_info.get('key')
        data = await request.json()
        new_value = data.get('value')
        state = self.cache_state.get(key, "I")
        
        # CASE 1: WRITE HIT (State M atau E)
        if state == "M" or state == "E":
            log.info(f"[{self.node_id}] WRITE HIT: '{key}'. State {state} -> M")
            self.update_cache(key, new_value, "M") # Cukup tulis lokal
        
        # CASE 2: WRITE HIT (State S)
        elif state == "S":
            log.info(f"[{self.node_id}] WRITE HIT: '{key}'. State S -> M. Broadcast INVALIDATE.")
            # Kirim "Invalidate" ke semua node lain
            self.metrics["invalidations_sent"] += 1
            await self.broadcast_bus_message(f"/bus/invalidate/{key}", {"key": key})
            self.update_cache(key, new_value, "M") # Tulis lokal & jadi Modified
        
        # CASE 3: WRITE MISS (State I atau tidak ada)
        else:
            log.warning(f"[{self.node_id}] WRITE MISS: '{key}'. State I -> M. Broadcast INVALIDATE.")
            # Kita perlu invalidasi yang lain (jika mereka punya)
            self.metrics["invalidations_sent"] += 1
            await self.broadcast_bus_message(f"/bus/invalidate/{key}", {"key": key})
            # Kita ambil data (meski kita timpa) & jadi Modified
            self.update_cache(key, new_value, "M")
        
        response_time = (time.time() - start_time) * 1000  # ms
        return web.json_response({
            "key": key, 
            "value": new_value, 
            "state": "M",
            "response_time_ms": round(response_time, 2)
        })

    # --- 2. Endpoint untuk "Bus Snooping" (Remote Request) ---

    async def handle_bus_read_miss(self, request: web.Request):
        """
        Handler untuk: POST /bus/read_miss/{key}
        NODE LAIN meminta data. Kita "snoop" request ini.
        """
        key = request.match_info.get('key')
        state = self.cache_state.get(key, "I")
        
        # Jika kita punya data yang valid (M, E, atau S)
        if state in ("M", "E", "S"):
            log.info(f"[{self.node_id}] BUS SNOOP (Read): '{key}' Hit! State {state} -> S")
            
            # Jika state kita M atau E, kita paksa jadi S (Shared)
            if state in ("M", "E"):
                self.cache_state[key] = "S"
                # (Dalam implementasi nyata, M akan write-back ke memori dulu)
                
            return web.json_response({"state": "S", "data": self.cache.get(key)})
            
        # Jika kita tidak punya, kembalikan Invalid
        return web.json_response({"state": "I"})

    async def handle_bus_invalidate(self, request: web.Request):
        """
        Handler untuk: POST /bus/invalidate/{key}
        NODE LAIN menulis data. Kita "snoop" request ini.
        """
        key = request.match_info.get('key')
        
        if key in self.cache_state and self.cache_state[key] != "I":
            self.metrics["invalidations_received"] += 1
            log.warning(f"[{self.node_id}] BUS SNOOP (Invalidate): '{key}' Hit! State -> I")
            # Paksa state kita jadi Invalid
            self.cache_state[key] = "I"
            
        return web.json_response({"status": "acked"})

    async def handle_root(self, request: web.Request):
        """
        Handler for GET / - Root endpoint
        """
        return web.json_response({
            "service": "Distributed Cache with MESI Protocol",
            "node_id": self.node_id,
            "cache_capacity": CACHE_CAPACITY,
            "current_items": len(self.cache),
            "endpoints": {
                "cache_operations": [
                    "GET /read/{key} - Read data",
                    "POST /write/{key} - Write data",
                    "GET /status - Show cache status",
                    "GET /metrics - Performance metrics"
                ],
                "bus_internal": [
                    "POST /bus/read_miss/{key} - Bus snooping",
                    "POST /bus/invalidate/{key} - Bus invalidation"
                ]
            }
        })

    # --- Endpoint untuk Debugging ---
    
    async def handle_get_status(self, request: web.Request):
        """Handler untuk GET /status (Melihat isi cache kita)"""
        uptime = time.time() - self.metrics["start_time"]
        hit_rate = 0
        if self.metrics["read_requests"] > 0:
            hit_rate = (self.metrics["cache_hits"] / self.metrics["read_requests"]) * 100
            
        return web.json_response({
            "node_id": self.node_id,
            "cache": self.cache,
            "cache_state": self.cache_state,
            "performance_metrics": {
                "uptime_seconds": round(uptime, 2),
                "cache_hit_rate_percent": round(hit_rate, 2),
                "total_reads": self.metrics["read_requests"],
                "total_writes": self.metrics["write_requests"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "invalidations_sent": self.metrics["invalidations_sent"],
                "invalidations_received": self.metrics["invalidations_received"],
                "bus_transactions": self.metrics["bus_transactions"],
                "cache_utilization_percent": round((len(self.cache) / CACHE_CAPACITY) * 100, 2)
            }
        })

    async def handle_metrics(self, request: web.Request):
        """Handler untuk GET /metrics (Detailed performance metrics)"""
        uptime = time.time() - self.metrics["start_time"]
        
        # Calculate additional metrics
        total_requests = self.metrics["read_requests"] + self.metrics["write_requests"]
        hit_rate = 0
        miss_rate = 0
        
        if self.metrics["read_requests"] > 0:
            hit_rate = (self.metrics["cache_hits"] / self.metrics["read_requests"]) * 100
            miss_rate = (self.metrics["cache_misses"] / self.metrics["read_requests"]) * 100
        
        throughput = total_requests / uptime if uptime > 0 else 0
        
        return web.json_response({
            "node_id": self.node_id,
            "timestamp": time.time(),
            "uptime_seconds": round(uptime, 2),
            "performance": {
                "requests_per_second": round(throughput, 2),
                "cache_hit_rate_percent": round(hit_rate, 2),
                "cache_miss_rate_percent": round(miss_rate, 2),
                "cache_utilization_percent": round((len(self.cache) / CACHE_CAPACITY) * 100, 2)
            },
            "counters": {
                "total_requests": total_requests,
                "read_requests": self.metrics["read_requests"],
                "write_requests": self.metrics["write_requests"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "invalidations_sent": self.metrics["invalidations_sent"],
                "invalidations_received": self.metrics["invalidations_received"],
                "bus_transactions": self.metrics["bus_transactions"]
            },
            "cache_info": {
                "current_items": len(self.cache),
                "max_capacity": CACHE_CAPACITY,
                "items": list(self.cache.keys())
            }
        })

    # --- Menjalankan Server ---
    
    async def run_server(self):
        app = web.Application()
        
        # Root endpoint
        app.router.add_get('/', self.handle_root)
        
        # Rute "CPU"
        app.router.add_get('/read/{key}', self.handle_local_read)
        app.router.add_post('/write/{key}', self.handle_local_write)
        app.router.add_get('/status', self.handle_get_status)
        app.router.add_get('/metrics', self.handle_metrics)
        
        # Rute "Bus"
        app.router.add_post('/bus/read_miss/{key}', self.handle_bus_read_miss)
        app.router.add_post('/bus/invalidate/{key}', self.handle_bus_invalidate)
        
        # --- UBAH BARIS INI ---
        # Matikan access log aiohttp yang berisik
        runner = web.AppRunner(app, access_log=None)
        # --- SELESAI UBAHAN ---
        
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        log.info(f"======= Cache Node {self.node_id} aktif di http://{self.host}:{self.port} =======")
        await asyncio.Event().wait()

# --- Titik Masuk Eksekusi Skrip ---
# --- UBAH SEMUA SETELAH INI ---

if __name__ == "__main__":
    # HAPUS semua kode 'argparse'

    NODE_ID = os.environ.get("NODE_ID", f"node-default-7000")
    PORT = int(os.environ.get("PORT", 7000))
    PEERS_STR = os.environ.get("PEERS", "")
    
    all_peer_names = PEERS_STR.split(',') if PEERS_STR else []
    other_peer_names = [p_name for p_name in all_peer_names if p_name != NODE_ID and p_name]
    
    HOST = "0.0.0.0" 
    
    node = CacheNode(
        host=HOST, 
        port=PORT, 
        node_id=NODE_ID, 
        peer_names=other_peer_names, 
        peer_port=PORT
    )
    
    try:
        asyncio.run(node.run_server())
    except KeyboardInterrupt:
        log.info(f"Shutting down {node.node_id}...")