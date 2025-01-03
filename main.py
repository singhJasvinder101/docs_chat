import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

from langchain_community.vectorstores import FAISS  # FAISS CPU here for very much pdf's together parallel processing use gpu
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:  # Check if text was extracted
                text += page_text
            else:
                print("No text found on this page.")
    print("Extracted text length:", len(text)) 
    return text




def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    print("text splitter ", text_splitter)
    chunks = text_splitter.split_text(text)
    print("chunks ", chunks)
    return chunks


def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embeddings)
    print("vector store ", vector_store)
    vector_store.save_local("faiss_index")  # store in local


def get_conversational_chain():
    prompt_template = """
    You are an intelligent assistant trained to answer questions based on the provided context. Please follow these guidelines:

    1. **Clarity**: Provide clear and concise answers.
    2. **Contextual Relevance**: Ensure your response is directly relevant to the context provided. Use the context to inform your answers.
    3. **Comprehensive Detail**: Where applicable, offer detailed explanations, examples, or additional information to enhance understanding.
    4. **Fallback**: If the answer is not found in the context, provide a relevant summary or related information. If still unsure, say, "I don't have more context about that."
    5. **Accuracy**: Avoid guessing; only provide information you are confident about.

    **Context**: {context}
    **Question**: {question}
    
    **Answer**:
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    print("model ", model)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    # create chain
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)  # chain_type stuff for internal summarizations also
    print("chain ", chain)
    return chain


def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.search(user_question, search_type="similarity")
    if not docs: 
        st.write("No relevant documents found for the question.")
        return

    
    chain = get_conversational_chain()
    
    response = chain(
        {"input_documents": docs, "question": user_question}, 
        return_only_outputs=True
    )
    print(response)
    st.write("Reply: ", response["output_text"])

    
def main():
    st.set_page_config("Chat PDF")
    st.header("Doc Chat")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Done")



if __name__ == "__main__":
    main()



