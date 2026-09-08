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
        Executes a Cypher query to calculate cognitive ranks dynamically, 
        archives nodes below the threshold, and returns the faded records for logging.
        """
        logger.info("Executing Neo4j Cognitive Decay Sweep.") 

        # Cypher query performing inline rank calculation, threshold filtering, and archival update
        decay_query = """
        MATCH (m:SemanticMemory)
        WHERE m.is_active = true 
          AND m.retention_policy IN ['EPHEMERAL', 'SHORT_TERM']
        WITH m,
             (m.importance_score * m.confidence * 
              CASE WHEN (1.0 + (m.strength - 1.0) * 0.2) > 3.0 THEN 3.0 
                   ELSE (1.0 + (m.strength - 1.0) * 0.2) END) /
             (1.0 + duration.between(datetime(m.last_accessed), datetime()).days * 0.05) AS current_rank
        WHERE current_rank < $decay_threshold
        SET m.is_active = false
        RETURN elementId(m) AS id, m.subject AS subject, m.predicate AS predicate, m.object AS object, current_rank AS rank
        """

        async with self.driver.session() as session:
            result = await session.run(decay_query, decay_threshold=self.decay_threshold)
            records = await result.data()

            if records:
                for record in records:
                    logger.info(
                        f"Memory {record['id']} [{record['subject']} -> {record['predicate']} -> {record['object']}] "
                        f"has faded (Rank: {record['rank']:.4f} < Threshold: {self.decay_threshold}). Archiving."
                    )
                logger.info(f"Archived {len(records)} decayed memories from Neo4j active state.")
            else:
                logger.info("Decay Sweep complete. All active transient memories remain stable and intact.")