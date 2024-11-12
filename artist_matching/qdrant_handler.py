import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
import os
import logging


def create_collection_if_not_exists(qdrant_client, collection_name):
    collections = qdrant_client.get_collections().collections
    if not any(collection.name == collection_name for collection in collections):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        logging.info(f"Created new collection: {collection_name}")
    else:
        logging.info(f"Collection {collection_name} already exists")

def add_to_vectorstore(text, tags, type, url):
    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_KEY"),
    )
    embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY"))
    # Connect to hacksc vectorstore
    collection_name = os.getenv("QDRANT_INDEX_NAME")
    create_collection_if_not_exists(qdrant_client, collection_name)

    # Add the text and tags (as metadata) to the vectorstore
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embed_model.get_text_embedding(text),
                payload={"text": text, "tags": tags, "type": type, "url": url}
            )
        ]
    )


    logging.info("Text added to vectorstore successfully")

def search_vectorstore(text, type, tags, collection_name):
    """
    Right now, the query tags are filtered to be a subset of the tags in the vectorstore.
    """

    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_KEY"),
    )
    embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY"))

    tag_filter_conditions = [
        models.FieldCondition(key="tags", match=models.MatchValue(value=tag))
        for tag in tags
    ]

    # Search the vectorstore
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=embed_model.get_text_embedding(text),
        limit=5,
        query_filter= models.Filter(
            must=[
                models.FieldCondition(key="type", match=models.MatchValue(value=type)),
            ],
            should=tag_filter_conditions,
        ),
    )

    logging.info(f"Retrieval results: {search_result}")

    # Return the search result
    return search_result
