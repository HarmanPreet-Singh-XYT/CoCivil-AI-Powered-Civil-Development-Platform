import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, OPENAI_API_KEY
from ingest import md_to_text

print("Loading test file...")
file_path = "../Hack Canada/City-Plan/Official Plan Chapter 1.md"
text = md_to_text(file_path)

doc = Document(
    page_content=text,
    metadata={
        "source": "City-Plan/Official Plan Chapter 1.md",
        "source_type": "markdown",
        "filename": "Official Plan Chapter 1.md"
    }
)

print("Chunking...")
# Fix imports as per previous replace_file_content
from langchain_text_splitters import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents([doc])
print(f"Created {len(chunks)} chunks.")

print("Embedding...")
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME
)
print(f"Test ingestion complete! Collection size: {vectorstore._collection.count()}")
