# src/nodes/queue_node.py
import asyncio
import os  # <-- TAMBAHKAN
import logging
# ... (impor lain tetap sama) ...

# ... (logging setup tetap sama) ...
# ... (REDIS_HOST & PORT) ...
# !! PENTING: Ubah REDIS_HOST agar menunjuk ke nama layanan Docker
REDIS_HOST = os.environ.get("REDIS_HOST", "redis") # <-- UBAH INI

class QueueNode:
    
    # --- UBAH FUNGSI __init__ ---
    def __init__(self, host: str, port: int, node_id: str, all_node_names: list):
        self.host = host
        self.port = port
        self.node_id = node_id
        self.peer_urls = {} # Peta node_id ke URL
        self.all_nodes = all_node_names # Daftar semua node_id (termasuk diri sendiri)
        
        peer_port = port # Asumsi semua di port yg sama
        for p_name in all_node_names:
            if p_name != self.node_id:
                self.peer_urls[p_name] = f"http://{p_name}:{peer_port}"
            
        self.redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
        
        self.hash_ring = ConsistentHashRing(replicas=10)
        for n_id in self.all_nodes:
            self.hash_ring.add_node(n_id)
            
        log.info(f"Node {self.node_id} dibuat. Ring: {self.all_nodes}")

    # ... (sisa fungsi class TETAP SAMA) ...
    # ... (get_redis_conn, handle_produce, handle_consume, dll) ...

# --- UBAH SEMUA SETELAH INI ---
if __name__ == "__main__":
    # HAPUS semua kode 'argparse'
    
    NODE_ID = os.environ.get("NODE_ID", f"node-default-9000")
    PORT = int(os.environ.get("PORT", 9000))
    # PEERS adalah string dipisah koma, misal: "queue-node-1,queue-node-2"
    PEERS_STR = os.environ.get("PEERS", "")
    
    all_node_names = PEERS_STR.split(',') if PEERS_STR else []

    HOST = "0.0.0.0"
    
    node = QueueNode(
        host=HOST, 
        port=PORT, 
        node_id=NODE_ID, 
        all_node_names=all_node_names
    )
    
    try:
        asyncio.run(node.run_server())
    except KeyboardInterrupt:
        log.info(f"Shutting down {node.node_id}...")