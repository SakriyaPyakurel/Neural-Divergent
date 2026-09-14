from neo4j import GraphDatabase

# Paste your new Aura URL and password directly here
URI = "neo4j+s://6161260c.databases.neo4j.io"
USER = "6161260c"
PASSWORD = "8ipSTgWjqyDTUDWa_Y-Vh2Wf0XMYmAMD1QN2PQFKx0o"

print("Attempting direct connection to Neo4j Aura...")
try:
  driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
  driver.verify_connectivity()
  print("✅ SUCCESS! Direct connection established successfully!")
  driver.close()
except Exception as e:
  print(f"❌ FAILED: {e}")