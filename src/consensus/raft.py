# src/consensus/raft.py

import asyncio
import random
import logging

log = logging.getLogger(__name__)

class RaftConsensus:
    """
    Mengelola logika state Raft (Follower, Candidate, Leader)
    dan proses election.
    """
    
    def __init__(self, node):
        # 'node' adalah referensi ke objek LockManagerNode
        # agar kita bisa mengakses self.node_id, self.peer_list,
        # dan self.broadcast_message()
        self.node = node 
        
        # Inisialisasi state Raft
        self.state = 'follower'
        self.current_term = 0
        self.voted_for = None
        self.votes_received = set()
        
        # Timer yang akan memicu election jika tidak di-reset
        self.election_timer_task = None
        
        # Timer untuk Leader mengirim heartbeat
        self.heartbeat_timer_task = None

    def get_election_timeout(self):
        """
        Waktu timeout harus acak untuk mencegah
        semua node menjadi candidate di waktu yang bersamaan.
        """
        return random.uniform(0.150, 0.300) # 150-300 ms

    async def start_election_timer(self):
        """
        Memulai "jam pasir". Jika habis, mulai election.
        """
        timeout = self.get_election_timeout()
        await asyncio.sleep(timeout)
        
        # Jika timer habis dan kita MASIH follower,
        # artinya kita tidak dapat heartbeat. Saatnya jadi candidate.
        if self.state == 'follower':
            log.warning(f"[{self.node.node_id}] Timeout! Tidak ada heartbeat. Memulai election...")
            await self.start_election()

    def reset_election_timer(self):
        """
        Me-reset "jam pasir". Dipanggil saat kita menerima
        heartbeat dari Leader atau saat kita memberi suara.
        """
        # Batalkan timer yang sedang berjalan (jika ada)
        if self.election_timer_task:
            self.election_timer_task.cancel()
            
        # Buat task timer baru
        self.election_timer_task = asyncio.create_task(self.start_election_timer())
        # log.info(f"[{self.node.node_id}] Timer di-reset.")

    async def start_election(self):
        """
        Proses untuk menjadi Candidate dan meminta suara.
        """
        # 1. Ubah state jadi Candidate
        self.state = 'candidate'
        
        # 2. Naikkan term (ronde pemilu)
        self.current_term += 1
        
        # 3. Beri suara untuk diri sendiri
        self.voted_for = self.node.node_id
        self.votes_received = {self.node.node_id} # Simpan suara kita
        
        log.info(f"[{self.node.node_id}] Menjadi CANDIDATE untuk Term {self.current_term}. Meminta suara...")

        # 4. Kirim RequestVote RPC (Remote Procedure Call) ke semua peer
        payload = {
            'type': 'request_vote',
            'term': self.current_term,
            'candidate_id': self.node.node_id
        }
        # Kita gunakan 'broadcast_message' dari node kita
        await self.node.broadcast_rpc("/request-vote", payload)
        
        # 5. Reset timer kita sendiri, untuk election berikutnya jika kita gagal
        self.reset_election_timer()

    def become_leader(self):
        """
        Dipanggil ketika kita menang pemilu.
        """
        if self.state != 'candidate':
            return # Hanya candidate yang bisa jadi leader

        log.info(f"👑 [{self.node.node_id}] Menang pemilu! Menjadi LEADER untuk Term {self.current_term} 👑")
        self.state = 'leader'
        
        # Batalkan timer election, ganti dengan timer heartbeat
        if self.election_timer_task:
            self.election_timer_task.cancel()
        
        # Mulai kirim heartbeat
        self.heartbeat_timer_task = asyncio.create_task(self.send_heartbeats())
        
    async def send_heartbeats(self):
        """
        Tugas Leader: kirim pesan 'AppendEntries' (heartbeat)
        secara periodik untuk mempertahankan kekuasaan.
        """
        while self.state == 'leader':
            # log.info(f"[{self.node.node_id}] Mengirim heartbeat...")
            payload = {
                'type': 'append_entries',
                'term': self.current_term,
                'leader_id': self.node.node_id
            }
            # Kirim ke semua peer, tapi jangan tunggu balasan (kirim & lupakan)
            asyncio.create_task(self.node.broadcast_rpc("/append-entries", payload))
            
            # Kirim heartbeat setiap 50ms
            await asyncio.sleep(0.050)
            
    def step_down(self, new_term):
        """
        Turun tahta (misal: kita menemukan Leader/Candidate
        dengan term yang lebih tinggi).
        """
        log.warning(f"[{self.node.node_id}] Turun tahta. Term baru: {new_term}")
        self.state = 'follower'
        self.current_term = new_term
        self.voted_for = None
        self.votes_received = set()
        
        # Jika kita tadinya Leader, hentikan pengiriman heartbeat
        if self.heartbeat_timer_task:
            self.heartbeat_timer_task.cancel()
            
        # Mulai lagi timer election
        self.reset_election_timer()