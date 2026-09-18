import asyncio
import logging 
from app.services.database import MemoryDatabase

logger = logging.getLogger('NeuralDivergent.DecayEngine') 

class CognitiveDecayEngine:
    """
    A lightweight, asynchronous worker that periodically checks active memory pools
    and cascades faded short/ephemeral knowledge into the archive.
    """
    def __init__(self, db: MemoryDatabase, check_interval_seconds: int = 3600, decay_threshold: float = 0.12):
        self.db = db 
        self.check_interval = check_interval_seconds 
        self.decay_threshold = decay_threshold
        self.is_running = False
        self._task = None 
    
    async def start(self):
        """Starts the Background Loop."""
        self.is_running = True
        self._task = asyncio.create_task(self._loop()) 
        logger.info("Cognitive Decay background engine started.") 

    async def stop(self):
        """Gracefully halts the loop""" 
        self.is_running = False 
        if self._task:
            self._task.cancel() 
            try: 
                await self._task 
            except asyncio.CancelledError:
                pass
        logger.info("Cognitive Decay Background engine stopped.")

    async def _loop(self):
        while self.is_running:
            try: 
                await self.run_decay_sweep() 
            except Exception as e:
                logger.error(f"Error during active decay sweep: {e}", exc_info=True)

            # Sleeping until the next sweep interval
            await asyncio.sleep(self.check_interval)
    
    async def run_decay_sweep(self):
        """
        Retrieves decayable memories from the SQLite database, checks their 
        cognitive rank against the threshold, and archives those that have faded.
        """
        logger.info("Executing SQLite Cognitive Decay Sweep.") 

        # Fetching all memories that are eligible for decay from SQLite
        records = self.db.get_decayable_memories()
        ids_to_archive = []

        # Checking which ones fall below threshold
        if records:
            for record in records:
                if record['current_rank'] < self.decay_threshold:
                    ids_to_archive.append(record['id'])
                    logger.info(
                        f"Memory {record['id']} [{record['subject']} -> {record['predicate']} -> {record['object']}] "
                        f"has faded (Rank: {record['current_rank']:.4f} < Threshold: {self.decay_threshold}). Archiving."
                    )

        # Archiving faded memories(if any)
        if ids_to_archive:
            self.db.archive_faded_memories(ids_to_archive)
            logger.info(f"Archived {len(ids_to_archive)} decayed memories from SQLite active state.")
        else:
            logger.info("Decay Sweep complete. All active transient memories remain stable and intact.")