"""
long_term_memory.py - main qdrant class for storage of ltm

Memoir+ a persona extension for Text Gen Web UI. 
MIT License

Copyright (c) 2024 brucepro

additional info here https://python-client.qdrant.tech/

"""

import random
from datetime import datetime, timedelta
from qdrant_client import models, QdrantClient
from qdrant_client.http.models import PointStruct
from html import escape
from sentence_transformers import SentenceTransformer

class LTM():
    def __init__(self,
                 collection,
                 ltm_limit,
                 verbose=False,
                 embedder='all-mpnet-base-v2',
                 address='localhost',
                 port=6333
                 ):

        self.verbose = verbose
        if self.verbose:
            print("initiating verbose debug mode.............")
        self.collection = collection
        self.ltm_limit = ltm_limit
        #print("LTM LIMIT:" + str(ltm_limit))
        self.address = address
        self.port = port
        if self.verbose:
            print(f"addr:{self.address}, port:{self.port}")

        self.embedder = embedder
        self. encoder = SentenceTransformer(self.embedder)
        self.qdrant = QdrantClient(self.address, port=self.port)
        self.create_vector_db_if_missing()

    
    def create_vector_db_if_missing(self):
        try:
            self.qdrant.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE
                )

            )
            if self.verbose:
                print(f"created self.collection: {self.collection}")
        except Exception as e:
            if self.verbose:
                vectors_count = self.qdrant.get_collection(
                    self.collection).vectors_count
                if self.verbose:
                    print(
                        f"self.collection: {self.collection} already exists with {vectors_count} vectors, not creating: {e}")

    def delete_vector_db(self):
        try:
            self.qdrant.delete_collection(
                collection_name=self.collection,
                )
            if self.verbose:
                print(f"deleted self.collection: {self.collection}")
        except Exception as e:
            if self.verbose:
                print(
                    f"self.collection: {self.collection} does not exists, not deleting: {e}")


    def store(self, doc_to_upsert):
        operation_info = self.qdrant.upsert(
            collection_name=self.collection,
            wait=True,
            points=self.get_embedding_vector(doc_to_upsert),
        )
        if self.verbose:
            print(operation_info)

    def get_embedding_vector(self, doc):
        data = doc['comment'] + doc['people']
        self.vector = self.encoder.encode(data).tolist()
        self.next_id = random.randint(0, 1e10)
        points = [
            PointStruct(id=self.next_id,
                        vector=self.vector,
                        payload=doc),
        ]
        return points

    def recall(self, query):
        self.query_vector = self.encoder.encode(query).tolist()

        results = self.qdrant.search(
            collection_name=self.collection,
            query_vector=self.query_vector,
            limit=self.ltm_limit + 1,
            score_threshold=0.1
        )
        return self.format_results_from_qdrant(results)
    
    def delete(self, comment_id):
        self.qdrant.delete_points(self.collection, [comment_id])
        self.logger.debug(f"Deleted comment with ID: {comment_id}")
        
    def format_results_from_qdrant(self, results):
        formated_results = []
        seen_comments = set()
        result_count = 0
        for result in results[1:]:
            comment = result.payload['comment']
            if comment not in seen_comments:
                seen_comments.add(comment)
                #formated_results.append("(" + result.payload['datetime'] + "'Memory':" + result.payload['comment'] + ", 'Emotions:" + result.payload['emotions'] + ", 'People':" + result.payload['people'] + ")")                
                #formated_results.append("(" + result.payload['datetime'] + "Memory:" + escape(result.payload['comment']) + ",Emotions:" + escape(result.payload['emotions']) + ",People:" + escape(result.payload['people']) + ")")
                datetime_obj = datetime.strptime(result.payload['datetime'], "%Y-%m-%dT%H:%M:%S.%f")
                date_str = datetime_obj.strftime("%Y-%m-%d")
                if result.score > 0.1:
                    if self.verbose:
                        print("score: " + str(result.score))
                    date_str = date_str + " score: " + str(result.score) 
                formated_results.append(result.payload['comment'] + ": on " + str(date_str))
                
            else:
                if self.verbose:
                    print("Not adding " + comment)
            result_count += 1
        return formated_results

    
    def get_last_summaries(self, range_hours):
        try:
            # Calculate the limit datetime
            now = datetime.now()
            limit_datetime = now - timedelta(hours=range_hours)
            limit_datetime_str = limit_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")
        except Exception as e:
            if self.verbose:
                print(f"Error calculating limit datetime: {e}")
            return []

        try:
            # Retrieve vectors with a filter on datetime
            query_vector = self.encoder.encode("").tolist()
            query_filter = {
                "must": [
                    {
                        "key": "datetime",
                        "range": {
                            "gte": limit_datetime_str
                        }
                    }
                ]
            }
            all_vectors = self.qdrant.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=10,
                query_filter=query_filter,
                score_threshold=0.1
            )
        except Exception as e:
            if self.verbose:
                print(f"Error retrieving vectors: {e}")
            return []

        formated_results = []
        seen_comments = set()
        result_count = 0
        for result in all_vectors:
            try:
                comment = result.payload['comment']
                if comment not in seen_comments:
                    seen_comments.add(comment)
                    datetime_obj = datetime.strptime(result.payload['datetime'], "%Y-%m-%dT%H:%M:%S.%f")
                    date_str = datetime_obj.strftime("%Y-%m-%d")
                    if self.verbose:
                        print("Adding memory to stm_context")
                    formated_results.append(result.payload['comment'] + ": on " + str(date_str))
                else:
                    if self.verbose:
                        print("Not adding " + comment)
                result_count += 1
            except Exception as e:
                if self.verbose:
                    print(f"Error processing result: {e}")
        return formated_results    


    def __repr__(self):
        return f"address: {self.address}, collection: {self.collection}"

    def __len__(self):
        return self.qdrant.get_collection(self.collection).vectors_count
