import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

import os

from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

from langchain.vectorstores import FAISS  # FAISS CPU here for very much pdf's together parallel processing use gpu
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_pdf_text(pdf_docs):
    text=""
    for pdf in pdf_docs:
        # read multiple pdf's
        pdf_reader= PdfReader(pdf)
        # read pages of each
        for page in pdf_reader.pages:
            text+= page.extract_text()
    return  text



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
    Answer the question as detailed as possible from the provided context, make sure to provide 
    all the details, If answer is not found in then try to provide most relevant data about it by your own, If still not found anyyhing just say "I don't have more context about that".
    don't provide the wrong answer if you are not sure about the answer.
    Context: {context}
    Question: {question}
    
    Answer:
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



