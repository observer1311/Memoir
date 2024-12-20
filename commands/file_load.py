"""
file_load.py - handles the loading of files from the ui

Memoir+ a persona extension for Text Gen Web UI. 
MIT License

Copyright (c) 2024 brucepro
"""

import requests
import os
from datetime import datetime, timedelta
from extensions.Memoir.rag.ingest_file_class import Ingest_File
from extensions.Memoir.rag.rag_data_memory import RagDataMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter


class File_Load():
    def __init__(self, character_name):
        self.character_name = character_name

    def read_file(self, file):
        load_file = Ingest_File(file)
        file_content = load_file.loadfile()
        
        #save to rag memory
        text_splitter = RecursiveCharacterTextSplitter(
separators=["\n"], chunk_size=1000, chunk_overlap=100, keep_separator=False
)
        verbose = False
        ltm_limit = 2
        address = "http://localhost:6333"
        rag = RagDataMemory(self.character_name,ltm_limit,verbose, address=address)
        for document in file_content:
            splits = text_splitter.split_text(document.page_content)
    
        for text in splits:
             #print("----")
             #print(text)
             #print("----")
             now = datetime.utcnow()
             data_to_insert = str(text) + " reference:" + str(file)
             doc_to_insert = {
                 'comment': str(data_to_insert),
                 'datetime': now,
                 'title': os.path.basename(file),
                 'rag_original_ref': os.path.basename(file)
             }
             rag.store(doc_to_insert)
        return f"[FILE_CONTENT={file}]\n{file_content}"

    def review_rag(self,file):
        address = "http://localhost:6333"
        rag = RagDataMemory(self.character_name,1,False, address=address)
        print(f"Reviewing RAG data for {self.character_name} : {file} ")
        results = rag.retrieve(file)
        if results:
            return results
        else:
            print(f"No matching data found for {file}")
            return []
