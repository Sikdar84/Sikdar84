# animal_shelter.py
from pymongo import MongoClient

class AnimalShelter:
    """
    AnimalShelter wraps a MongoDB collection and provides basic CRUD:
      - create(document)
      - read(query)
      - update(query, new_values)
      - delete(query)
    """
    def __init__(self, username, password, host='localhost', port=27017, database_name="aac", collection_name="animals"):
        try:
            uri = f"mongodb://{username}:{password}@{host}:{port}/{database_name}?authSource={database_name}"
            self.client = MongoClient(uri)
            self.database = self.client[database_name]
            self.collection = self.database[collection_name]
            print(f"MongoDB connection successful to database '{database_name}' (collection '{collection_name}').")
        except Exception as e:
            print("Error connecting to MongoDB:", e)
            raise


    # --------------------------
    # CREATE operation
    # --------------------------
     def create(self, data):
        try:
            result = self.collection.insert_one(data)
            return True if result.inserted_id else False
        except Exception as e:
            print("Error inserting document:", e)
            return False


    # --------------------------
    # READ operation
    # --------------------------
     def read(self, query={}):
        try:
            documents = list(self.collection.find(query))
            return documents
        except Exception as e:
            print("Error reading documents:", e)
            return []

    # --------------------------
    # UPDATE operation
    # --------------------------
     def update(self, query, new_values):
        try:
            result = self.collection.update_many(query, {"$set": new_values})
            return result.modified_count
        except Exception as e:
            print("Error updating documents:", e)
            return 0

    # --------------------------
    # DELETE operation
    # --------------------------
     def delete(self, query):
        try:
            result = self.collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            print("Error deleting documents:", e)
            return 0
