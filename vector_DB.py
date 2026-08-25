from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from chuncking import split_text_into_chunks
from uuid import uuid4
import os
from utils import debug_print
from langchain.tools import tool
from websocket import send_tool_update
from dotenv import load_dotenv
load_dotenv()
MODEL = os.getenv("MODEL")


if MODEL == "local":
    from sentence_transformers import SentenceTransformer

    MODEL_PATH = "./models/bge-small-en-v1.5"
    embedding_model = SentenceTransformer(MODEL_PATH)

    def embedd(texts, **kwargs):
        return embedding_model.encode(texts, **kwargs)

    VECTOR_SIZE = embedding_model.get_sentence_embedding_dimension()

elif MODEL == "remote":
    from openai import OpenAI
    import numpy as np

    _openai_client = OpenAI()
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL",
        "text-embedding-3-small"
    )

    def embedd(texts, **kwargs):
        response = _openai_client.embeddings.create(
            model=EMBEDDING_MODEL_NAME,
            input=texts,
        )

        vectors = np.array(
            [item.embedding for item in response.data],
            dtype=np.float32
        )

        if kwargs.get("normalize_embeddings"):
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = vectors / norms

        return vectors

    # Get the dimension from the remote embedding model
    VECTOR_SIZE = len(
        embedd("dimension probe", normalize_embeddings=False)[0]
    )

else:
    raise ValueError(
        f"Unknown MODEL value: '{MODEL}'. "
        "Set MODEL to 'local' or 'remote' in .env"
    )

QDRANT_PATH = "./data/qdrant"
COLLECTION_NAME = "research_documents"

client = QdrantClient(path=QDRANT_PATH)





# Create collection if it doesn't exist
if not client.collection_exists(COLLECTION_NAME):

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )


@tool("upsert_file", description="Upsert a file into the vector database.")
def upsert_file(file_path, session_id):
    chunks = split_text_into_chunks(file_path)
    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings
    vectors = embedd(texts, normalize_embeddings=True)

    points = []

    for chunk, vector in zip(chunks, vectors):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector.tolist(),
                payload={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "chunk_index": chunk["chunk_index"],
                    "session_id": session_id,
                },
            )
        )


    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)

def upsert_file_func(file_path, session_id):
    chunks = split_text_into_chunks(file_path)
    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings
    vectors = embedd(texts, normalize_embeddings=True)

    points = []

    for chunk, vector in zip(chunks, vectors):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector.tolist(),
                payload={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "chunk_index": chunk["chunk_index"],
                    "session_id": session_id,
                },
            )
        )


    client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def close_client():
    """Properly close the Qdrant client connection to prevent shutdown errors."""
    if client is not None:
        try:
            client.close()
        except Exception:
            pass  # Ignore errors during shutdown


@tool("retrieve_top_k", description="Retrieve top k relevant documents from the vector database.")
def retrieve_top_k(query, session_id, k=5):

    debug_print(f"Retrieving top {k} relevant documents for query: '{query}' and session_id: '{session_id}'")
    send_tool_update(f"Retrieving top {k} relevant documents for query: '{query}' and session_id: '{session_id}'")
    query_vector = embedd([query], normalize_embeddings=True)[0].tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,

        query_filter=Filter(must=[FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id),
                )
            ]
        ),

        limit=k,
        with_payload=True,
    )
    return results.points

if __name__ == "__main__":
    #chunk and upsert all files into folder Files
    session_id = "public"

    files_dir = "./Files"
    supported_exts = (".pdf", ".txt", ".md", ".docx", ".csv", ".xlsx", ".json")

    for filename in os.listdir(files_dir):
        file_path = os.path.join(files_dir, filename)
        if os.path.isfile(file_path) and filename.lower().endswith(supported_exts):
            count = upsert_file_func(file_path, session_id)
            debug_print(f"Upserted {count} chunks from {filename}")

    client.close()
    
import atexit
atexit.register(close_client)