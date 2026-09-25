from fastembed import TextEmbedding

class EmbeddingEngine:
    def __init__(self,model:str="BAAI/bge-small-en-v1.5"):
        self.embedder_model = TextEmbedding(model)
    
    def generate_embeddings(self,text:str):
        embeddings = list(self.embedder_model.embed([text]))
        return embeddings[0].tolist()