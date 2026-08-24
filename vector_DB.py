from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance,VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from chuncking import split_text_into_chunks
from uuid import uuid4


# Define constants
MODEL_PATH = "./models/bge-small-en-v1.5"
embedding_model = SentenceTransformer(MODEL_PATH)
QDRANT_PATH = "./data/qdrant"
COLLECTION_NAME = "research_documents"
client = QdrantClient(path=QDRANT_PATH)
VECTOR_SIZE = embedding_model.get_embedding_dimension()


# Create collection if it doesn't exist
if not client.collection_exists(COLLECTION_NAME):

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

def upsert_file(file_path, session_id):
    chunks = split_text_into_chunks(file_path)
    texts = [chunk["text"] for chunk in chunks]

    # Generate embeddings
    vectors = embedding_model.encode(texts,normalize_embeddings=True,)

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

    client.upsert(collection_name=COLLECTION_NAME,points=points)
    return len(points)


from langchain.tools import tool

@tool("retrieve_top_k", description="Retrieve top k relevant documents from the vector database.")
def retrieve_top_k(query, session_id, k=5):

    query_vector = embedding_model.encode(query,normalize_embeddings=True).tolist()

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
    file_path = "Files\Vinayak Mishra Resume.pdf"
    session_id = "session_1"


    num_points = upsert_file(file_path, session_id)
    print(f"Inserted {num_points} points into the collection '{COLLECTION_NAME}'.")


    keyword = input("Enter a keyword to search: ")
    results = retrieve_top_k(keyword, session_id, k=5)

    for i, point in enumerate(results):
        print(f"Result {i + 1}:")
        print(f"Score: {point.score}")
        print(f"Text: {point.payload['text']}")
        print(f"Source: {point.payload['source']}")
        print(f"Chunk Index: {point.payload['chunk_index']}")
        print("="*25)

    client.close()
