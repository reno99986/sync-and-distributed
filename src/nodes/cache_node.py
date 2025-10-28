# src/nodes/cache_node.py
import asyncio
import os  # <-- TAMBAHKAN
import logging
# ... (impor lain tetap sama) ...

# ... (logging setup tetap sama) ...

class CacheNode:
    
    # --- UBAH FUNGSI __init__ ---
    def __init__(self, host: str, port: int, node_id: str, peer_names: list, peer_port: int):
        self.host = host
        self.port = port
        self.node_id = node_id
        self.peer_urls = {}
        
        for p_name in peer_names:
            self.peer_urls[p_name] = f"http://{p_name}:{peer_port}"

        # ... (sisa cache, state, dan memori tetap sama) ...
        
        log.info(f"Cache Node {self.node_id} dibuat. Peers: {list(self.peer_urls.keys())}")
    
    # ... (sisa fungsi class TETAP SAMA) ...
    # ... (handle_local_read, handle_bus_read_miss, dll) ...

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