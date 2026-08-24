from sentence_transformers import SentenceTransformer

from qdrant_client import QdrantClient
from qdrant_client.models import Distance,VectorParams, PointStruct

QDRANT_PATH = "./data/qdrant"
COLLECTION_NAME = "research_documents"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"



