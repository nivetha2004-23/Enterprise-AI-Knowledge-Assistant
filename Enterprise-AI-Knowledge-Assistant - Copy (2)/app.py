import streamlit as st
import os
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS


# Load .env
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)

st.markdown("""
<h1 style='text-align: center; color:#4CAF50;'>
📊 Enterprise AI Knowledge Assistant
</h1>
<p style='text-align: center; color:gray;'>
Powered by Gemini + FAISS + RAG Architecture
</p>
""", unsafe_allow_html=True)
st.sidebar.title("📄 PDF Information")
st.markdown(
    "<p style='text-align:center; color:gray;'>"
    "Developed by Nivetha | AI PDF Chatbot Project"
    "</p>",
    unsafe_allow_html=True
)
st.sidebar.markdown("## ⚙️ System Info")
st.sidebar.write("🧠 Model: Gemini 2.5 Flash")
st.sidebar.write("📚 Embeddings: gemini-embedding-001")
st.sidebar.write("📦 Vector DB: FAISS")
st.sidebar.write("🤖 Mode: RAG Chatbot")
if "messages" not in st.session_state:
    st.session_state.messages = []
uploaded_file = st.file_uploader(
    "Upload a PDF",
    type=["pdf"]
)
if uploaded_file is not None:
    if (
        "current_file" not in st.session_state
        or st.session_state.current_file != uploaded_file.name
    ):
        st.session_state.current_file = uploaded_file.name

        if "vector_store" in st.session_state:
            del st.session_state["vector_store"]

        st.session_state.messages = []
if uploaded_file is None:
    st.info("📄 Please upload a PDF first.")
    st.stop()
if "vector_store" not in st.session_state:
    with st.spinner("📄 Processing PDF..."):
        pdf = PdfReader(uploaded_file)

        text = ""

        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        if not text.strip():
            st.error("❌ No readable text found in this PDF.")
            st.stop()

        chunks = text_splitter.split_text(text)

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key
        )
        vector_store = FAISS.from_texts(
            texts=chunks,
            embedding=embeddings
        )
        st.session_state.vector_store = vector_store
vector_store = st.session_state["vector_store"]    

st.success("✅ PDF is ready! Ask your questions below.")
st.sidebar.success("PDF Uploaded Successfully")
st.sidebar.write("📄 File Name:", uploaded_file.name)
#st.sidebar.write("📑 Number of Chunks:", len(chunks))
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []

    if "vector_store" in st.session_state:
        del st.session_state["vector_store"]

    st.rerun()
chat = ""

for msg in st.session_state.messages:
    chat += f'{msg["role"]}: {msg["content"]}\n\n'

st.sidebar.download_button(
    "⬇️ Download Chat",
    data=chat,
    file_name="chat_history.txt",
    mime="text/plain"
)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"**{msg['role'].title()}**")
        st.write(msg["content"])
        if msg["role"] == "assistant" and "source" in msg:
            st.caption("📄 Source")
            st.code(msg["source"][:300])
user_input = st.chat_input("Ask something from your PDF...")

if user_input:
    if "vector_store" not in st.session_state:
        st.error("Please upload a PDF first.")
        st.stop()

    vector_store = st.session_state["vector_store"]
    
    st.session_state.messages.append({"role": "user", "content": user_input})

    docs_with_score = vector_store.similarity_search_with_score(user_input, k=3)
    if docs_with_score:
        source = docs_with_score[0][0].page_content
    else:
        source = "No source found."

    context = "\n\n".join([doc.page_content for doc, score in docs_with_score])

    if not context.strip():
        response_text = "Answer not found in the document."
    else:
        prompt = f"""
Use ONLY the PDF context.

Context:
{context}

Question:
{user_input}
"""

        try:
            with st.spinner("🤖 Thinking..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                response_text = getattr(response, "text", "No response generated.")

        except Exception as e:
            response_text = f"⚠️ {e}"

    st.session_state.messages.append(
        {"role": "assistant", "content": response_text,"source":source}
    )

    with st.chat_message("assistant"):
        st.write(response_text)
        st.caption("📄 Source")

        st.code(source[:300])
        st.markdown("---")
        