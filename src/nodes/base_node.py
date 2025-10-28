# src/nodes/base_node.py

import asyncio
import argparse
import logging
from aiohttp import web

# Impor fungsi 'send_message' dari file yang kita buat sebelumnya
from src.communication.message_passing import send_message

# Mengatur logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

class BaseNode:
    """
    Representasi dasar dari sebuah node dalam sistem terdistribusi.
    Setiap node menjalankan server HTTP-nya sendiri dan tahu cara menghubungi node lain (peers).
    """
    def __init__(self, host: str, port: int, peer_ports: list):
        self.host = host
        self.port = port
        self.node_id = f"node-{port}" # Kita gunakan port sebagai ID unik untuk kesederhanaan
        
        # peer_list adalah kamus (dict) yang memetakan node_id peer ke URL lengkapnya
        # misal: {"node-8002": "http://127.0.0.1:8002", "node-8003": "http://127.0.0.1:8003"}
        self.peer_list = {}
        for p_port in peer_ports:
            peer_id = f"node-{p_port}"
            self.peer_list[peer_id] = f"http://{host}:{p_port}"
        
        log.info(f"Node {self.node_id} dibuat. Peers: {list(self.peer_list.keys())}")

    # --- Bagian Server (Menerima Pesan) ---

    async def handle_receive(self, request: web.Request):
        """
        Handler untuk endpoint POST /receive.
        Ini dipanggil setiap kali node ini menerima pesan.
        """
        try:
            data = await request.json()
            # Tampilkan pesan yang diterima di konsol
            log.info(f"[{self.node_id}] Menerima pesan: {data.get('content')} dari {data.get('sender_id')}")
            return web.json_response({"status": "ok", "message": "Pesan diterima"}, status=200)
        except Exception as e:
            log.error(f"Error saat memproses pesan: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    # --- Bagian Klien (Mengirim Pesan) ---

    async def broadcast_message(self, content: str):
        """
        Mengirim pesan ke SEMUA peer di self.peer_list.
        """
        log.info(f"[{self.node_id}] Melakukan broadcast: '{content}'")
        
        # Buat payload standar
        payload = {
            "sender_id": self.node_id,
            "content": content
        }
        
        # Buat daftar 'task' untuk dikerjakan secara bersamaan (concurrently)
        tasks = []
        for peer_url in self.peer_list.values():
            # Setiap peer mendapat 'task' send_message-nya sendiri
            # Kita targetkan endpoint /receive di node peer
            tasks.append(
                send_message(f"{peer_url}/receive", payload)
            )
        
        # Menjalankan semua task secara paralel dan menunggu semuanya selesai
        await asyncio.gather(*tasks)

    # --- Handler untuk Uji Coba Manual ---
    
    async def handle_send_test(self, request: web.Request):
        """
        Handler untuk endpoint GET /send (HANYA UNTUK TESTING).
        Ini memicu node untuk mengirim pesan ke semua peernya.
        """
        try:
            message = request.query.get('msg', f"Hello dari {self.node_id}")
            # Panggil fungsi broadcast kita
            # Kita jalankan di background (create_task) agar request HTTP ini bisa langsung dibalas
            asyncio.create_task(self.broadcast_message(message))
            
            return web.Response(text=f"OK, mengirim '{message}' ke {len(self.peer_list)} peers.")
        except Exception as e:
            return web.Response(text=f"Error: {e}", status=500)

    # --- Menjalankan Server ---
    
    async def run_server(self):
        """
        Menginisialisasi dan menjalankan server HTTP aiohttp.
        """
        app = web.Application()
        
        # Daftarkan rute (endpoints) dan handler-nya
        app.router.add_post('/receive', self.handle_receive)
        app.router.add_get('/send', self.handle_send_test) # Endpoint untuk tes
        
        # Setup dan jalankan server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        log.info(f"======= Node {self.node_id} aktif di http://{self.host}:{self.port} =======")
        
        # Baris ini penting agar server tetap berjalan selamanya
        await asyncio.Event().wait()

# --- Titik Masuk Eksekusi Skrip ---

if __name__ == "__main__":
    # argparse digunakan untuk membaca argumen dari command line
    # (misal: --port 8001 --peers 8002 8003)
    parser = argparse.ArgumentParser(description="Run a BaseNode for the distributed system.")
    parser.add_argument('--port', type=int, required=True, help='Port untuk menjalankan node ini.')
    parser.add_argument('--peers', type=int, nargs='+', required=True, help='Daftar port dari semua node peer.')
    
    args = parser.parse_args()
    
    # Buat instance BaseNode
    node = BaseNode(host="127.0.0.1", port=args.port, peer_ports=args.peers)
    
    try:
        # Jalankan server
        asyncio.run(node.run_server())
    except KeyboardInterrupt:
        log.info(f"Shutting down {node.node_id}...")