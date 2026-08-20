import logging 
from typing import List,Dict,Any,Tuple 
from app.services.graph_manager import GraphManager 

logger = logging.getLogger("NeuralDivergent.RetrievalPlanner") 

class RetrievalPlanner:
    def __init__(self,graph_manager:GraphManager):
        self.graph_manager = graph_manager

    def classify_intent(self,query:str) -> str:
        """
        Determines whether the query requires Graph Memory retrieval or Direct handling.
        """
        # Triggers that indicate multi-hop or historical graph lookup is needed
        graph_triggers = [
            "remember", "recall", "my preference", "allergic", "what did i",
            "history", "project", "building", "favorite", "who", "relationship"
        ]
        query_lower = query.lower() 
        if any(trigger in query_lower for trigger in graph_triggers) or len(query.split()) > 8:
            return "GRAPH"
        return "DIRECT"

    def fetch_active_subgraph(self, user_id: str, max_hops: int = 2, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Traverses Neo4j 1-2 hops from the User node, pruning inactive nodes/edges.
        """
        # Safely casting max_hops to integer for Cypher string interpolation
        safe_hops = int(max_hops)

        query = f"""
        MATCH (u:User {{user_id: $user_id}})
        MATCH path = (u)-[*1..{safe_hops}]-(target)
        WHERE ALL(rel IN relationships(path) WHERE rel.is_active IS NULL OR rel.is_active = true)
          AND ALL(node IN nodes(path) WHERE node.is_active IS NULL OR node.is_active = true)
        WITH path, relationships(path) AS rels
        RETURN 
            [n IN nodes(path) | {{id: id(n), labels: labels(n), props: properties(n)}}] AS nodes,
            [r IN rels | {{type: type(r), props: properties(r)}}] AS relationships
        LIMIT $limit
        """
        
        try:
            with self.graph_manager.driver.session() as session:
                result = session.run(query, user_id=user_id, limit=limit)
                records = [record.data() for record in result]
                return records
        except Exception as e:
            logger.error(f"Error fetching sub-graph for user {user_id}: {e}")
            return []

    def serialize_to_dsl(self, paths: List[Dict[str, Any]]) -> str:
        """
        Compresses extracted Neo4j paths into a hyper-dense Domain Specific Language (DSL)
        format to reduce LLM token usage.
        
        Example Output:
        (User:user_1) -[ALLERGIC_TO]-> (Concept:peanuts)
        (Concept:peanuts) -[INFERRED_FROM]-> (Deduction:d_99 {confidence: 0.95})
        """
        if not paths:
            return "No prior relevant memory found."

        serialized_triplets = set()

        for path in paths:
            nodes = path.get("nodes", [])
            rels = path.get("relationships", [])

            for i in range(len(rels)):
                start_node = nodes[i]
                end_node = nodes[i + 1]
                rel = rels[i]

                # Extracting primary label & identifying property
                start_label = start_node["labels"][0] if start_node["labels"] else "Node"
                start_id = start_node["props"].get("name") or start_node["props"].get("user_id") or start_node["props"].get("statement") or "Entity"

                end_label = end_node["labels"][0] if end_node["labels"] else "Node"
                end_id = end_node["props"].get("name") or end_node["props"].get("statement") or end_node["props"].get("text") or "Entity"

                rel_type = rel["type"]

                triplet = f"({start_label}:{start_id}) -[{rel_type}]-> ({end_label}:{end_id})"
                serialized_triplets.add(triplet)

        return "\n".join(serialized_triplets)

    def prepare_context(self, user_id: str, query: str,max_hops:int=2) -> Tuple[str, str]:
        """
        Orchestrates routing, extraction, and compression into a single prompt payload.
        Returns: (route_type, serialized_context)
        """
        route = self.classify_intent(query)
        
        if route == "DIRECT":
            return "DIRECT", "No long-term memory lookup required."

        # Passes max_hops forward into the fetch function
        paths = self.fetch_active_subgraph(user_id=user_id,max_hops=max_hops)
        compressed_dsl = self.serialize_to_dsl(paths)
        
        return "GRAPH", compressed_dsl