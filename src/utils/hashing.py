# src/utils/hashing.py

import hashlib
import bisect

class ConsistentHashRing:
    """
    Implementasi consistent hash ring sederhana.
    """
    
    def __init__(self, replicas=3):
        """
        Args:
            replicas (int): Jumlah 'virtual nodes' per node fisik.
                            Meningkatkan ini akan membuat distribusi
                            data lebih merata.
        """
        self.replicas = replicas
        # _keys adalah sorted list dari hash values
        self._keys = []
        # _nodes adalah pemetaan dari hash value (int) ke node_id (str)
        self._nodes = {}

    def _hash(self, key: str) -> int:
        """Helper untuk mengubah string jadi integer hash."""
        # Menggunakan md5 lalu ambil 4 byte pertama dan konversi ke integer
        return int.from_bytes(hashlib.md5(key.encode()).digest()[:4], 'big')

    def add_node(self, node_id: str):
        """
        Menambahkan node fisik ke dalam ring.
        Setiap node fisik akan diwakili oleh 'replicas' virtual nodes.
        """
        for i in range(self.replicas):
            # Buat hash untuk "node_id:replica_index"
            key = f"{node_id}:{i}"
            h = self._hash(key)
            
            # Tambahkan hash ke sorted list
            bisect.insort(self._keys, h)
            # Petakan hash tersebut ke node_id
            self._nodes[h] = node_id

    def remove_node(self, node_id: str):
        """Menghapus node fisik (dan semua replikanya) dari ring."""
        for i in range(self.replicas):
            key = f"{node_id}:{i}"
            h = self._hash(key)
            
            # Hati-hati saat menghapus dari list
            try:
                # Cari index dari hash
                index = bisect.bisect_left(self._keys, h)
                # Pastikan hash-nya benar-benar ada di index itu
                if self._keys[index] == h:
                    self._keys.pop(index)
                    
                del self._nodes[h]
            except (ValueError, IndexError):
                pass # Abaikan jika tidak ada

    def get_node(self, key: str) -> str:
        """
        Mendapatkan node_id yang bertanggung jawab atas 'key' (misal: topic name).
        """
        if not self._keys:
            return None

        # Hash 'key' (topic name)
        h = self._hash(key)
        
        # Cari 'posisi' hash tersebut di dalam sorted list
        # 'bisect_right' menemukan titik sisip di kanan
        index = bisect.bisect_right(self._keys, h)
        
        # Jika index-nya di paling akhir, kita 'wrap around' ke
        # node pertama (index 0)
        if index == len(self._keys):
            index = 0
            
        # Kembalikan node_id yang ada di posisi hash tersebut
        return self._nodes[self._keys[index]]