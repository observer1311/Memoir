"""
commandhandler.py - main class that parses the chat and checks for commands to run

Memoir+ a persona extension for Text Gen Web UI. 
MIT License

Copyright (c) 2024 brucepro
 
"""

from extensions.Memoir.persona.persona import Persona
from extensions.Memoir.commands.urlhandler import UrlHandler
from extensions.Memoir.commands.file_load import File_Load
from extensions.Memoir.rag.rag_data_memory import RagDataMemory

import os
import re
from sqlite3 import connect
import pathlib
import validators

class CommandHandler():
    def __init__(self, db_path, character_name):
        self.db_path = db_path
        self.character_name = character_name
        self.commands = {}
        self.command_output = {}
        self.flags = {}

    def process_command(self, input_string):
        pattern = r'\[([^\[\]]+)\]'
        commands_in_string = re.findall(pattern, input_string, re.IGNORECASE)
        commands_list = []
        for cmd in commands_in_string:
            command_processed = False
            if "=" in cmd:
                command_processed = True
                print("Processing = command..." + str(cmd))
                command_parts = cmd.split('=')
                # if parts1 contains | , split on this rather than ',' to allow for commas in the content use a variable "split_char" to store the split character
                if "|" in command_parts[1]:
                    split_char = "|"
                else:
                    split_char = ","
                commands_list.append({command_parts[0]: {f"arg{i+1}": arg for i, arg in enumerate(command_parts[1].split(split_char))}})
            if not command_processed and ":" in cmd:
                command_processed = True
                print("Processing : command..." + str(cmd))
                command_parts1 = cmd.split(',')
                for item in command_parts1:
                    command_parts2 = item.split(':')
                    if len(command_parts2) > 1:
                        commands_list.append({command_parts2[0].strip(): {f"arg{i+1}": arg.strip() for i, arg in enumerate(command_parts2[1].split(','))}})
        
        if len(commands_list) > 0:
            unique_cmds = []
            for cmd in commands_list:
                if cmd not in unique_cmds:
                    unique_cmds.append(cmd)
                    
            for cmd in unique_cmds:
                if isinstance(cmd, dict) and "GET_URL" in cmd:
                    args = cmd["GET_URL"]
                    handler = UrlHandler(self.character_name)
                    url = str(args.get("arg1"))
                    mode = str(args.get("arg2")).lower().strip() if args.get("arg2") else 'output'
                    validation = validators.url(url)
                    if validation:
                        print("URL is valid")
                        content = handler.get_url(url, mode=mode)
                        self.command_output["GET_URL"] = f"GET_URL: {content}"
                    else:
                        print("URL is invalid")
                        self.command_output["GET_URL"] = f"GET_URL: URL is invalid"
                
                if isinstance(cmd, dict) and "FILE_LOAD" in cmd:
                    args = cmd["FILE_LOAD"]
                    file = str(args.get("arg1"))
                    file_load_handler = File_Load(self.character_name)
                    validation = validators.url(file)
                    is_url = False
                    if validation:
                        print("File is url")
                        is_url = True
                        content = file_load_handler.read_file(file)
                        self.command_output["FILE_LOAD"] = f"FILE_LOAD: {content}"
                    if not is_url and os.path.exists(file):
                        print("Path exist")
                        if os.path.isfile(file):
                            print("Path leads to a file")
                            content = file_load_handler.read_file(file)
                            self.command_output["FILE_LOAD"] = f"FILE_LOAD: {content}"
                        elif os.path.isdir(file):
                            print("Path leads to a directory. This will skip adding to content due to likelihood of extreme length.")
                            count = 0
                            for file in os.listdir(file):
                                path = os.path.join(file, file)
                                file_load_handler.read_file(path)
                                count += 1
                            self.command_output["FILE_LOAD"] = f"FILE_LOAD: Successfully ingested {count} total documents."
                        else:
                            print("File does not exist")
                            self.command_output["FILE_LOAD"] = "FILE_LOAD: File doesn't exist"
                
                if isinstance(cmd, dict) and "REVIEW_RAG" in cmd:
                    args = cmd["REVIEW_RAG"]
                    file = str(args.get("arg1"))
                    file_load_handler = File_Load(self.character_name)
                    results = file_load_handler.review_rag(file)
                    content = ""
                    for result in results:
                        content += result + "\n"
                    self.flags['disable_rag'] = True
                    self.command_output["REVIEW_RAG"] = f"REVIEW_RAG: {content}"
                
                if isinstance(cmd, dict) and "INSERT_RAG" in cmd:
                    args = cmd["INSERT_RAG"]
                    title = str(args.get("arg1"))
                    text = str(args.get("arg2"))
                    rag_handler = RagDataMemory(self.character_name, 10, verbose=True)
                    rag_handler.insert_rag_data(title, text)
                    self.command_output["INSERT_RAG"] = f"INSERT_RAG: Successfully inserted title '{title}' with text '{text}'"

        return "\n".join([f"{k}: {v}" for k, v in self.command_output.items()])