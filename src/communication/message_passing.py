# src/communication/message_passing.py

import aiohttp
import asyncio
import logging

# Mengatur logging dasar untuk melihat output
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# src/communication/message_passing.py
# (Pastikan di-update)

import aiohttp
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def send_message(target_url: str, payload: dict):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(target_url, json=payload) as response:
                response.raise_for_status()
                # Coba baca JSON, tapi jika gagal (misal balasan kosong),
                # kembalikan dict kosong
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    return {} # Kembalikan dict kosong jika tidak ada JSON
                
        except aiohttp.ClientConnectorError:
            log.error(f"Gagal terhubung ke {target_url}. Node mungkin offline.")
            return None # Kembalikan None jika node down
        except Exception as e:
            log.error(f"Error saat mengirim pesan ke {target_url}: {e}")
            return None # Kembalikan None untuk error lain