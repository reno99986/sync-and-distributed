# src/nodes/queue_node.py
import asyncio
import os  # <-- TAMBAHKAN
import logging
import time
import uuid
from aiohttp import web
import redis

from src.communication.message_passing import send_message
# from src.algorithms.consistent_hashing import ConsistentHashRing
from src.utils.hashing import ConsistentHashRing

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# !! PENTING: Ubah REDIS_HOST agar menunjuk ke nama layanan Docker
REDIS_HOST = os.environ.get("REDIS_HOST", "redis") # <-- UBAH INI
REDIS_PORT = 6379

class QueueNode:
    """
    Node untuk message queue dengan consistent hashing.
    """
    
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
            
        # Message acknowledgment tracking
        # Format: {"message_id": {"queue": "queue_name", "message": "content", "consumer": "client_id", "timestamp": time}}
        self.pending_acks = {}
        
        # Cleanup task will be started in run_server()
        self.cleanup_task = None
            
        log.info(f"Node {self.node_id} dibuat. Ring: {self.all_nodes}")

    def get_redis_conn(self):
        """Mendapatkan koneksi Redis dari pool."""
        return redis.Redis(connection_pool=self.redis_pool)

    async def cleanup_unacked_messages(self):
        """
        Background task to requeue messages that haven't been acknowledged
        """
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                current_time = time.time()
                expired_messages = []
                
                for msg_id, msg_info in self.pending_acks.items():
                    # If message is unacked for more than 60 seconds, requeue it
                    if current_time - msg_info["timestamp"] > 60:
                        expired_messages.append(msg_id)
                
                for msg_id in expired_messages:
                    msg_info = self.pending_acks.pop(msg_id)
                    # Requeue the message
                    r = self.get_redis_conn()
                    r.lpush(msg_info["queue"], msg_info["message"])
                    log.warning(f"[{self.node_id}] Requeued unacked message: {msg_id} to {msg_info['queue']}")
                    
            except Exception as e:
                log.error(f"[{self.node_id}] Error in cleanup task: {e}")

    async def handle_produce(self, request: web.Request):
        """
        Handler untuk POST /produce
        Menambahkan pesan ke queue.
        """
        data = await request.json()
        queue_name = data.get('queue')
        message = data.get('message')
        
        if not queue_name or not message:
            return web.json_response({"error": "queue dan message harus diisi"}, status=400)
        
        # Tentukan node yang bertanggung jawab untuk queue ini
        responsible_node = self.hash_ring.get_node(queue_name)
        
        if responsible_node == self.node_id:
            # Kita yang bertanggung jawab, simpan ke Redis
            r = self.get_redis_conn()
            r.rpush(queue_name, message)
            log.info(f"[{self.node_id}] Pesan ditambahkan ke queue '{queue_name}': {message}")
            return web.json_response({"status": "success", "handled_by": self.node_id})
        else:
            # Forward ke node yang bertanggung jawab
            target_url = f"{self.peer_urls[responsible_node]}/produce"
            log.info(f"[{self.node_id}] Forwarding ke {responsible_node}")
            response = await send_message(target_url, data)
            return web.json_response(response if response else {"error": "Node tidak merespons"})

    async def handle_consume(self, request: web.Request):
        """
        Handler untuk POST /consume
        Mengambil pesan dari queue dengan at-least-once delivery guarantee.
        Body: {"queue": "queue_name", "consumer_id": "client_id"}
        """
        data = await request.json()
        queue_name = data.get('queue')
        consumer_id = data.get('consumer_id', 'anonymous')
        
        if not queue_name:
            return web.json_response({"error": "queue harus diisi"}, status=400)
        
        # Tentukan node yang bertanggung jawab
        responsible_node = self.hash_ring.get_node(queue_name)
        
        if responsible_node == self.node_id:
            # Kita yang bertanggung jawab
            r = self.get_redis_conn()
            message = r.lpop(queue_name)
            
            if message:
                # Generate unique message ID for tracking
                message_id = str(uuid.uuid4())
                message_content = message.decode('utf-8')
                
                # Track message for acknowledgment
                self.pending_acks[message_id] = {
                    "queue": queue_name,
                    "message": message_content,
                    "consumer": consumer_id,
                    "timestamp": time.time()
                }
                
                log.info(f"[{self.node_id}] Pesan diambil dari queue '{queue_name}': {message_content} (ID: {message_id})")
                return web.json_response({
                    "status": "success",
                    "message": message_content,
                    "message_id": message_id,
                    "handled_by": self.node_id,
                    "note": "Please acknowledge this message using /ack endpoint"
                })
            else:
                return web.json_response({
                    "status": "empty",
                    "message": None,
                    "handled_by": self.node_id
                })
        else:
            # Forward ke node yang bertanggung jawib
            target_url = f"{self.peer_urls[responsible_node]}/consume"
            log.info(f"[{self.node_id}] Forwarding ke {responsible_node}")
            response = await send_message(target_url, data)
            return web.json_response(response if response else {"error": "Node tidak merespons"})

    async def handle_acknowledge(self, request: web.Request):
        """
        Handler untuk POST /ack
        Acknowledge message consumption to ensure at-least-once delivery
        Body: {"message_id": "uuid"}
        """
        data = await request.json()
        message_id = data.get('message_id')
        
        if not message_id:
            return web.json_response({"error": "message_id harus diisi"}, status=400)
        
        if message_id in self.pending_acks:
            # Remove from pending acknowledgments
            msg_info = self.pending_acks.pop(message_id)
            log.info(f"[{self.node_id}] Message acknowledged: {message_id} from queue '{msg_info['queue']}'")
            return web.json_response({
                "status": "success",
                "message": "Message acknowledged",
                "handled_by": self.node_id
            })
        else:
            return web.json_response({
                "status": "error",
                "message": "Message ID not found or already acknowledged"
            })

    async def handle_queue_status(self, request: web.Request):
        """
        Handler untuk GET /status - Show queue status
        """
        r = self.get_redis_conn()
        queue_info = {}
        
        # Get all queue keys
        for key in r.scan_iter(match="*"):
            queue_name = key.decode('utf-8')
            length = r.llen(queue_name)
            queue_info[queue_name] = length
        
        return web.json_response({
            "node_id": self.node_id,
            "queues": queue_info,
            "pending_acks": len(self.pending_acks),
            "hash_ring_nodes": self.all_nodes
        })

    async def handle_root(self, request: web.Request):
        """
        Handler for GET / - Root endpoint
        """
        return web.json_response({
            "service": "Distributed Queue System",
            "node_id": self.node_id,
            "hash_ring_nodes": self.all_nodes,
            "endpoints": {
                "queue_operations": [
                    "POST /produce - Add message to queue",
                    "POST /consume - Get message from queue",
                    "POST /ack - Acknowledge message",
                    "GET /status - Show queue status"
                ]
            }
        })

    async def run_server(self):
        """
        Menjalankan server HTTP.
        """
        app = web.Application()
        
        # Root endpoint
        app.router.add_get('/', self.handle_root)
        
        # Daftarkan endpoint
        app.router.add_post('/produce', self.handle_produce)
        app.router.add_post('/consume', self.handle_consume)
        app.router.add_post('/ack', self.handle_acknowledge)
        app.router.add_get('/status', self.handle_queue_status)
        
        # --- UBAH BARIS INI ---
        # Matikan access log aiohttp yang berisik
        runner = web.AppRunner(app, access_log=None)
        # --- SELESAI UBAHAN ---
        
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        # Start cleanup task setelah event loop berjalan
        self.cleanup_task = asyncio.create_task(self.cleanup_unacked_messages())
        
        log.info(f"======= Queue Node {self.node_id} aktif di http://{self.host}:{self.port} =======")
        
        await asyncio.Event().wait()

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