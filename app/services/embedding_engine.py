from sentence_transformers import SentenceTransformer

class EmbeddingEngine:
    def __init__(self,model:str='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(f"sentence-transformers/{model}")
    
    def generate_embeddings(self,text:str):
        return self.model.encode(text).tolist()