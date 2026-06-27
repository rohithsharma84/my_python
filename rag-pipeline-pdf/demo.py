"""
To build an RAG-powered FAQ agent using LangChain, FAISS, and an LLM that retrieves relevant 
document chunks and generates grounded, source-backed answers to solve ungrounded or inconsistent 
responses and speed up accurate support
"""

from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA

load_dotenv()

# Load the documents and split them into chunks
loader = TextLoader("faq.txt")
documents = loader.load()

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

# Generate embeddings for the document chunks
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=os.environ["OPENAI_API_KEY"])
vectorstore = FAISS.from_documents(docs, embeddings)

# Initialize the LLM and the RetrievalQA chain
llm = ChatOpenAI(model="gpt-5-mini", api_key=os.environ["OPENAI_API_KEY"])
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    return_source_documents=True
)

# Ask a question and get an answer with source documents
while True:
    query = input("Ask a question (or type 'exit' to quit): ")
    if query.lower() == "exit":
        break

    result = qa_chain.invoke(query)
    answer = result['result']
    source_docs = result['source_documents']

    print("\nAnswer:")
    print(answer)
    print("\nSource Documents:")
    for i, doc in enumerate(result["source_documents"], 1):
        print(f"\nSource {i}:- \n{doc.page_content}")