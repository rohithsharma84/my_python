# Create a RAG pipeline over sample PDFs and let user ask questions

import os
from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate

load_dotenv()

# Step 1: Load PDF documents from the working directory
pdf_files = [
    "data/1762517560_course_end_project_problem_statement.pdf",
    "data/ref-FAISS.pdf",
    "data/ref-PyPDFLoader.pdf"
]

documents = []
for file in pdf_files:
    # PyPDFLoader reads each page of the PDF as a separate document
    loader = PyPDFLoader(file_path=file, extraction_mode="layout")
    documents.extend(loader.load())

# Step 2: Split documents into smaller chunks for embedding
# chunk_overlap ensures context is not lost at chunk boundaries
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = text_splitter.split_documents(documents)

# Print chunking statistics as required by the project
print(f"Total chunks: {len(docs)}")
avg_size = sum(len(d.page_content) for d in docs) / len(docs)
print(f"Average chunk size: {avg_size:.0f} chars")

# Step 3: Load the OpenAI API key from the environment (.env file)
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")
api_key = SecretStr(os.getenv("OPENAI_API_KEY"))

# Step 4: Generate embeddings and store in FAISS vector database
# text-embedding-ada-002 converts each chunk into a dense vector for similarity search
embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002",
    api_key=api_key
)
vectorstore = FAISS.from_documents(docs, embeddings)

# Step 5: Initialize the LLM for generating answers
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL_NAME", "gpt-5-mini"),
    api_key=api_key
)

# Custom prompt instructs the LLM to answer using only the retrieved context
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="Answer in 2-3 sentences using only the context below.\n\nContext: {context}\n\nQuestion: {question}\nAnswer:"
)

# Step 6: Build the RetrievalQA chain
# The chain retrieves relevant chunks from FAISS, then passes them to the LLM
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(),
    return_source_documents=True,
    chain_type_kwargs={"prompt": prompt}
)

# Step 7: Accept user queries and display answers with source references
while True:
    query = input("Ask a question (or type 'q' to quit): ")
    if query.lower() == "q":
        break

    result = qa_chain.invoke(query)
    answer = result['result']
    source_docs = result['source_documents']

    print("\nAnswer:")
    print(answer)
    print("\nSource Documents:")
    for i, doc in enumerate(source_docs, 1):
        content = doc.page_content
        source = doc.metadata.get('source', 'unknown')
        page = doc.metadata.get('page', 'unknown')
        truncated = '(truncated)' if len(content) > 50 else ''
        print(f"\nSource {i} [{source}, page {page}]:-")
        print(f"{content[:50]}{truncated}")
