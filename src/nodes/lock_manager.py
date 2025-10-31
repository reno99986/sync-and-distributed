# src/nodes/lock_manager.py

import asyncio
import os  # <-- TAMBAHKAN untuk membaca environment variables
import logging
from aiohttp import web

# Impor utilitas komunikasi kita
from src.communication.message_passing import send_message
# Impor OTAK Raft yang baru kita buat
from src.consensus.raft import RaftConsensus

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

class LockManagerNode:
    """
    Node ini menjalankan server HTTP dan mengelola logika Raft Consensus.
    """
    
    # --- UBAH FUNGSI __init__ ---
    def __init__(self, host: str, port: int, node_id: str, peer_names: list, peer_port: int):
        self.host = host
        self.port = port
        self.node_id = node_id  # <-- Gunakan node_id dari env
        
        self.peer_list = {}
        for p_name in peer_names:
            # Bangun URL peer menggunakan nama layanan Docker
            # Nama layanan bisa langsung di-resolve oleh Docker network
            self.peer_list[p_name] = f"http://{p_name}:{peer_port}"
        
        # INI BAGIAN PENTING:
        # Buat instance dari otak Raft.
        # Kita 'pass' 'self' agar 'RaftConsensus' bisa memanggil
        # fungsi di 'LockManagerNode' (seperti broadcast_rpc).
        self.raft = RaftConsensus(self)
        
        # Lock Management State Machine
        # Format: {"resource_id": {"type": "shared/exclusive", "holders": [list_of_clients], "queue": [waiting_clients]}}
        self.lock_data = {}
        
        # Deadlock Detection: Track lock dependencies
        # Format: {"client_id": {"waiting_for": "resource_id", "holding": [list_of_resources]}}
        self.client_dependencies = {}
        
        log.info(f"Node {self.node_id} dibuat. Peers: {list(self.peer_list.keys())}")

    # --- Komunikasi (Mirip BaseNode) ---

    async def broadcast_rpc(self, endpoint: str, payload: dict):
        """
        Mengirim pesan RPC (seperti /request-vote) ke SEMUA peer.
        """
        tasks = []
        for peer_id, peer_url in self.peer_list.items():
            target_url = f"{peer_url}{endpoint}"
            tasks.append(
                # Kita 'pass' peer_id untuk logging balasan
                self.send_rpc(peer_id, target_url, payload)
            )
        
        # Jalankan semua RPC secara paralel dan tunggu hasilnya
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_rpc(self, peer_id: str, target_url: str, payload: dict):
        """
        Wrapper untuk 'send_message' yang memproses balasan.
        """
        try:
            response = await send_message(target_url, payload)
            if response:
                # Proses balasan RPC di sini
                await self.handle_rpc_response(peer_id, payload, response)
        except Exception as e:
            log.error(f"Error mengirim RPC ke {target_url}: {e}")

    # --- Logika Pemrosesan RPC ---

    async def handle_rpc_response(self, peer_id: str, request_payload: dict, response: dict):
        """
        Memproses balasan dari RPC yang kita kirim.
        """
        # Cek apakah response memiliki term yang lebih tinggi
        response_term = response.get('term', 0)
        if response_term > self.raft.current_term:
            log.info(f"[{self.node_id}] Menerima term lebih tinggi {response_term} dari {peer_id}")
            self.raft.step_down(response_term)
            return
            
        if self.raft.state != 'candidate':
            # Jika kita bukan candidate lagi, abaikan balasan suara
            return 
            
        if request_payload.get('type') == 'request_vote':
            # Jika ini adalah balasan untuk permintaan suara
            if response.get('vote_granted'):
                log.info(f"[{self.node_id}] Mendapat suara YA dari {peer_id}")
                self.raft.votes_received.add(peer_id)
                
                # Cek apakah kita sudah menang (suara mayoritas)
                # Mayoritas = (jumlah_node / 2) + 1
                # (len(self.peer_list) + 1) adalah total node termasuk diri kita
                mayoritas = ((len(self.peer_list) + 1) // 2) + 1
                log.info(f"[{self.node_id}] Total suara: {len(self.raft.votes_received)}/{mayoritas}")
                if len(self.raft.votes_received) >= mayoritas:
                    self.raft.become_leader()
            else:
                log.info(f"[{self.node_id}] Mendapat suara TIDAK dari {peer_id}")
                
        # Tidak perlu logic kompleks untuk restart election di sini
        # Biarkan election timeout handle restart otomatis


    # --- Lock Management Functions ---
    
    def detect_deadlock(self, client_id: str, resource_id: str) -> bool:
        """
        Simple deadlock detection using cycle detection in wait-for graph
        """
        visited = set()
        rec_stack = set()
        
        def has_cycle(current_client):
            if current_client in rec_stack:
                return True
            if current_client in visited:
                return False
                
            visited.add(current_client)
            rec_stack.add(current_client)
            
            # Check what this client is waiting for
            if current_client in self.client_dependencies:
                waiting_resource = self.client_dependencies[current_client].get("waiting_for")
                if waiting_resource and waiting_resource in self.lock_data:
                    # Check who holds this resource
                    holders = self.lock_data[waiting_resource].get("holders", [])
                    for holder in holders:
                        if has_cycle(holder):
                            return True
            
            rec_stack.remove(current_client)
            return False
        
        return has_cycle(client_id)

    def acquire_lock(self, resource_id: str, client_id: str, lock_type: str) -> dict:
        """
        Acquire lock logic (only executed on Leader)
        """
        if self.raft.state != 'leader':
            return {"status": "error", "message": "Not leader"}
        
        # Initialize resource if not exists
        if resource_id not in self.lock_data:
            self.lock_data[resource_id] = {
                "type": None,
                "holders": [],
                "queue": []
            }
        
        lock_info = self.lock_data[resource_id]
        
        # Check if client already holds this lock
        if client_id in lock_info["holders"]:
            return {"status": "success", "message": "Already holding lock"}
        
        # Case 1: No one holds the lock
        if not lock_info["holders"]:
            lock_info["type"] = lock_type
            lock_info["holders"].append(client_id)
            
            # Update client dependencies
            if client_id not in self.client_dependencies:
                self.client_dependencies[client_id] = {"waiting_for": None, "holding": []}
            self.client_dependencies[client_id]["holding"].append(resource_id)
            
            log.info(f"[{self.node_id}] Lock acquired: {client_id} -> {resource_id} ({lock_type})")
            return {"status": "success", "message": "Lock acquired"}
        
        # Case 2: Shared lock requested and current lock is shared
        elif lock_type == "shared" and lock_info["type"] == "shared":
            lock_info["holders"].append(client_id)
            
            if client_id not in self.client_dependencies:
                self.client_dependencies[client_id] = {"waiting_for": None, "holding": []}
            self.client_dependencies[client_id]["holding"].append(resource_id)
            
            log.info(f"[{self.node_id}] Shared lock acquired: {client_id} -> {resource_id}")
            return {"status": "success", "message": "Shared lock acquired"}
        
        # Case 3: Lock is held, need to wait
        else:
            # Check for deadlock before adding to queue
            if self.detect_deadlock(client_id, resource_id):
                log.warning(f"[{self.node_id}] Deadlock detected! Rejecting {client_id} -> {resource_id}")
                return {"status": "error", "message": "Deadlock detected, request rejected"}
            
            # Add to waiting queue
            if client_id not in lock_info["queue"]:
                lock_info["queue"].append(client_id)
                
                # Update client dependencies
                if client_id not in self.client_dependencies:
                    self.client_dependencies[client_id] = {"waiting_for": None, "holding": []}
                self.client_dependencies[client_id]["waiting_for"] = resource_id
            
            log.info(f"[{self.node_id}] Lock queued: {client_id} waiting for {resource_id}")
            return {"status": "waiting", "message": "Added to queue"}

    def release_lock(self, resource_id: str, client_id: str) -> dict:
        """
        Release lock logic (only executed on Leader)
        """
        if self.raft.state != 'leader':
            return {"status": "error", "message": "Not leader"}
        
        if resource_id not in self.lock_data:
            return {"status": "error", "message": "Resource not found"}
        
        lock_info = self.lock_data[resource_id]
        
        if client_id not in lock_info["holders"]:
            return {"status": "error", "message": "Client does not hold this lock"}
        
        # Remove from holders
        lock_info["holders"].remove(client_id)
        
        # Update client dependencies
        if client_id in self.client_dependencies:
            if resource_id in self.client_dependencies[client_id]["holding"]:
                self.client_dependencies[client_id]["holding"].remove(resource_id)
        
        log.info(f"[{self.node_id}] Lock released: {client_id} -> {resource_id}")
        
        # Process waiting queue if no more holders
        if not lock_info["holders"] and lock_info["queue"]:
            next_client = lock_info["queue"].pop(0)
            
            # Grant lock to next client (assume they want exclusive for simplicity)
            lock_info["type"] = "exclusive"
            lock_info["holders"].append(next_client)
            
            # Update dependencies
            if next_client in self.client_dependencies:
                self.client_dependencies[next_client]["waiting_for"] = None
                self.client_dependencies[next_client]["holding"].append(resource_id)
            
            log.info(f"[{self.node_id}] Lock granted from queue: {next_client} -> {resource_id}")
        
        return {"status": "success", "message": "Lock released"}

    # --- REST API Endpoints for Lock Management ---
    
    async def handle_acquire_lock(self, request: web.Request):
        """
        Handler for POST /acquire
        Body: {"resource_id": "resource1", "client_id": "client1", "lock_type": "shared/exclusive"}
        """
        try:
            data = await request.json()
            resource_id = data.get('resource_id')
            client_id = data.get('client_id')
            lock_type = data.get('lock_type', 'exclusive')
            
            if not resource_id or not client_id:
                return web.json_response({"error": "resource_id and client_id required"}, status=400)
            
            if lock_type not in ['shared', 'exclusive']:
                return web.json_response({"error": "lock_type must be 'shared' or 'exclusive'"}, status=400)
            
            result = self.acquire_lock(resource_id, client_id, lock_type)
            return web.json_response(result)
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_release_lock(self, request: web.Request):
        """
        Handler for POST /release
        Body: {"resource_id": "resource1", "client_id": "client1"}
        """
        try:
            data = await request.json()
            resource_id = data.get('resource_id')
            client_id = data.get('client_id')
            
            if not resource_id or not client_id:
                return web.json_response({"error": "resource_id and client_id required"}, status=400)
            
            result = self.release_lock(resource_id, client_id)
            return web.json_response(result)
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_lock_status(self, request: web.Request):
        """
        Handler for GET /locks - Show current lock status
        """
        return web.json_response({
            "node_id": self.node_id,
            "raft_state": self.raft.state,
            "locks": self.lock_data,
            "dependencies": self.client_dependencies
        })

    async def handle_root(self, request: web.Request):
        """
        Handler for GET / - Root endpoint
        """
        return web.json_response({
            "service": "Distributed Lock Manager",
            "node_id": self.node_id,
            "raft_state": self.raft.state,
            "current_term": self.raft.current_term,
            "endpoints": {
                "lock_management": [
                    "POST /acquire - Acquire lock",
                    "POST /release - Release lock", 
                    "GET /locks - Show lock status"
                ],
                "raft_internal": [
                    "POST /request-vote - Raft RPC",
                    "POST /append-entries - Raft RPC"
                ]
            }
        })

    # --- Endpoint Server (Menerima Pesan) ---

    async def handle_request_vote(self, request: web.Request):
        """
        Handler untuk endpoint POST /request-vote.
        Dipanggil saat Candidate meminta suara kita.
        """
        data = await request.json()
        candidate_term = data.get('term')
        candidate_id = data.get('candidate_id')
        
        vote_granted = False
        
        # 1. Cek apakah term si candidate lebih baru dari kita
        if candidate_term > self.raft.current_term:
            # Jika ya, kita otomatis 'step_down' dan update term
            self.raft.step_down(candidate_term)

        # 2. Logika memberi suara
        if (candidate_term == self.raft.current_term) and \
           (self.raft.voted_for is None or self.raft.voted_for == candidate_id):
            # Jika term-nya sama DAN kita belum vote (atau kita vote dia lagi)
            vote_granted = True
            self.raft.voted_for = candidate_id
            self.raft.reset_election_timer() # Kita reset timer kita karena kita berpartisipasi
            log.info(f"[{self.node_id}] Memberi suara YA untuk {candidate_id} di Term {self.raft.current_term}")
        
        return web.json_response({
            "term": self.raft.current_term,
            "vote_granted": vote_granted
        })

    async def handle_append_entries(self, request: web.Request):
        """
        Handler untuk endpoint POST /append-entries.
        Ini adalah "heartbeat" dari Leader.
        """
        data = await request.json()
        leader_term = data.get('term')
        
        if leader_term < self.raft.current_term:
            # Jika ada Leader 'abal-abal' dari term lama, tolak
            return web.json_response({"term": self.raft.current_term, "success": False})

        # Jika kita menerima heartbeat, berarti Leader-nya sah.
        # Kita reset "jam pasir" kita.
        self.raft.reset_election_timer()
        
        if leader_term > self.raft.current_term:
            # Jika term Leader lebih baru, kita akui dia
            self.raft.step_down(leader_term)
        
        # Pastikan kita adalah follower
        if self.state == 'candidate':
            self.raft.step_down(leader_term)
        elif self.state == 'leader':
            # Ini aneh, ada 2 leader. Kita 'step_down'.
            self.raft.step_down(leader_term)
        
        # log.info(f"[{self.node_id}] Heartbeat diterima dari {data.get('leader_id')}")
        
        return web.json_response({"term": self.raft.current_term, "success": True})

    # --- Menjalankan Server ---
    
    async def run_server(self):
        """
        Menginisialisasi dan menjalankan server HTTP aiohttp.
        """
        app = web.Application()
        
        # Root endpoint
        app.router.add_get('/', self.handle_root)
        
        # Lock Management API
        app.router.add_post('/acquire', self.handle_acquire_lock)
        app.router.add_post('/release', self.handle_release_lock)
        app.router.add_get('/locks', self.handle_lock_status)
        
        # Raft RPC endpoints (internal)
        app.router.add_post('/request-vote', self.handle_request_vote)
        app.router.add_post('/append-entries', self.handle_append_entries)
        
        # --- UBAH BARIS INI ---
        # Matikan access log aiohttp yang berisik
        runner = web.AppRunner(app, access_log=None)
        # --- SELESAI UBAHAN ---
        
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        log.info(f"======= Node {self.node_id} aktif di http://{self.host}:{self.port} (State: {self.raft.state}) =======")
        
        # MULAI "JAM PASIR" PERTAMA KALI
        self.raft.reset_election_timer()
        
        await asyncio.Event().wait()

    # --- Properti untuk akses mudah ke state Raft ---
    @property
    def state(self):
        return self.raft.state

# --- Titik Masuk Eksekusi Skrip ---
# --- UBAH SEMUA SETELAH INI ---

if __name__ == "__main__":
    # HAPUS semua kode 'argparse'
    
    # Baca konfigurasi dari Environment Variables
    # NODE_ID: Identitas unik node ini (misal: "lock-node-1")
    NODE_ID = os.environ.get("NODE_ID", f"node-default-8000")
    
    # PORT: Port tempat node ini akan listening
    PORT = int(os.environ.get("PORT", 8000))
    
    # PEERS: String berisi daftar nama semua node (termasuk diri sendiri)
    # dipisah koma, misal: "lock-node-1,lock-node-2,lock-node-3"
    PEERS_STR = os.environ.get("PEERS", "")
    
    # Parse string PEERS menjadi list
    all_peer_names = PEERS_STR.split(',') if PEERS_STR else []
    
    # Daftar peer adalah semua nama, KECUALI diri kita sendiri
    # Filter: hapus nama diri sendiri dan string kosong
    other_peer_names = [p_name for p_name in all_peer_names if p_name != NODE_ID and p_name]
    
    # Host harus 0.0.0.0 untuk Docker agar bisa menerima koneksi dari luar container
    HOST = "0.0.0.0" 
    
    # Buat instance node dengan konfigurasi dari environment
    node = LockManagerNode(
        host=HOST, 
        port=PORT, 
        node_id=NODE_ID, 
        peer_names=other_peer_names, 
        peer_port=PORT  # Asumsi semua peer ada di port yang sama
    )
    
    try:
        asyncio.run(node.run_server())
    except KeyboardInterrupt:
        log.info(f"Shutting down {node.node_id}...")