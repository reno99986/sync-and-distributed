# src/nodes/lock_manager.py
import asyncio
import os  # <-- TAMBAHKAN
import logging
from aiohttp import web
from src.communication.message_passing import send_message
from src.consensus.raft import RaftConsensus

# ... (logging setup tetap sama) ...

class LockManagerNode:
    
    # --- UBAH FUNGSI __init__ ---
    def __init__(self, host: str, port: int, node_id: str, peer_names: list, peer_port: int):
        self.host = host
        self.port = port
        self.node_id = node_id # <-- Gunakan node_id dari env
        
        self.peer_list = {}
        for p_name in peer_names:
            # Bangun URL peer menggunakan nama layanan
            self.peer_list[p_name] = f"http://{p_name}:{peer_port}"
        
        self.raft = RaftConsensus(self)
        self.lock_data = {} 
        
        log.info(f"Node {self.node_id} dibuat. Peers: {list(self.peer_list.keys())}")
    
    # ... (sisa fungsi class TETAP SAMA) ...
    # ... (handle_request_vote, handle_append_entries, run_server, dll) ...

# --- UBAH SEMUA SETELAH INI ---
if __name__ == "__main__":
    # HAPUS semua kode 'argparse'
    
    # Baca konfigurasi dari Environment Variables
    NODE_ID = os.environ.get("NODE_ID", f"node-default-8000")
    PORT = int(os.environ.get("PORT", 8000))
    # PEERS adalah string dipisah koma, misal: "lock-node-1,lock-node-2,lock-node-3"
    PEERS_STR = os.environ.get("PEERS", "")
    
    all_peer_names = PEERS_STR.split(',') if PEERS_STR else []
    
    # Daftar peer adalah semua nama, KECUALI diri kita sendiri
    other_peer_names = [p_name for p_name in all_peer_names if p_name != NODE_ID and p_name]
    
    # Host harus 0.0.0.0 untuk Docker
    HOST = "0.0.0.0" 
    
    node = LockManagerNode(
        host=HOST, 
        port=PORT, 
        node_id=NODE_ID, 
        peer_names=other_peer_names, 
        peer_port=PORT # Asumsi semua peer ada di port yang sama
    )
    
    try:
        asyncio.run(node.run_server())
    except KeyboardInterrupt:
        log.info(f"Shutting down {node.node_id}...")