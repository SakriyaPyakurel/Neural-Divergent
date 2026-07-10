import asyncio
import logging 
from app.services.database import MemoryDatabase

logger = logging.getLogger('NeuralDivergent.DecayEngine') 

class CognitiveDecayEngine:
    """
    A lightweight, asynchronous worker that periodically checks active memory pools
    and cascades faded short/emphemeral knowledge into the archive.
    """
    def __init__(self,db:MemoryDatabase,check_interval_seconds:int=3600,decay_threshold:float=0.12):
        self.db = db 
        self.check_interval = check_interval_seconds 
        self.decay_threshold = decay_threshold
        self.is_running = False
        self._task = None 
    
    async def start(self):
        """Starts the Background Loop."""
        self.is_running=True
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
                logger.error(f"Error during active decay sweep: {e}",exc_info=True)

            # Sleeping until the next sweep interval
            await asyncio.sleep(self.check_interval)
    
    async def run_decay_sweep(self):
        """Evaluates active memories and purges faded context."""
        logger.info("Executing Cognitive Decay Sweep.") 
        decayable_memories = self.db.get_decayable_memories()

        faded_ids = [] 
        for mem in decayable_memories:
            current_rank = mem.get("current_rank",0.0) 

            # If a memory's rank has decayed has below threshold,marking it for archival 
            if current_rank < self.decay_threshold:
                logger.info(
                    f"Memory {mem['id']} [{mem['subject']} -> {mem['predicate']} -> {mem['object']}]"
                    f"has faded (Rank: {current_rank:.4f} < Threshold: {self.decay_threshold}). Archiving."
                )
                faded_ids.append(mem['id'])

        if faded_ids:
            self.db.archive_faded_memories(faded_ids)
        else:
            logger.info("Decay Sweep complete. All active transient memories remain stable and intact.")
