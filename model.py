"""
model.py - Model component of MVC architecture
Contains the AnimalShelter class for MongoDB CRUD operations
Author: Manoj Chaudhary
Course: CS 499 Capstone
Date: May 2026
"""

import logging
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('animal_shelter.log'),
        logging.StreamHandler()
    ]
)


class AnimalShelter:
    """
    AnimalShelter wraps a MongoDB collection and provides CRUD operations.
    
    This class handles all database interactions for the animal shelter
    application, including create, read, update, and delete operations.
    
    Attributes:
        client (MongoClient): MongoDB client connection
        database (Database): MongoDB database reference
        collection (Collection): MongoDB collection reference
    """
    
    def __init__(self, username=None, password=None, host='localhost', 
                 port=27017, database_name="aac", collection_name="animals"):
        """
        Initialize MongoDB connection with credential validation.
        
        Args:
            username (str): MongoDB username (defaults to env var)
            password (str): MongoDB password (defaults to env var)
            host (str): MongoDB host address
            port (int): MongoDB port number
            database_name (str): Name of the database
            collection_name (str): Name of the collection
            
        Raises:
            ValueError: If credentials are missing
            ConnectionError: If MongoDB connection fails
        """
        # Load credentials from environment if not provided
        self.username = username or os.getenv('MONGODB_USERNAME')
        self.password = password or os.getenv('MONGODB_PASSWORD')
        
        # Validate credentials
        if not self.username or not self.password:
            error_msg = "Database credentials not found. Set MONGODB_USERNAME and MONGODB_PASSWORD in .env file"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Construct MongoDB URI
            uri = f"mongodb://{self.username}:{self.password}@{host}:{port}/{database_name}?authSource={database_name}"
            
            # Create MongoDB client
            self.client = MongoClient(uri)
            
            # Verify connection
            self.client.admin.command('ping')
            
            # Set database and collection
            self.database = self.client[database_name]
            self.collection = self.database[collection_name]
            
            logging.info(f"MongoDB connection successful to database '{database_name}' (collection '{collection_name}')")
            print(f"MongoDB connection successful to database '{database_name}' (collection '{collection_name}')")
            
        except Exception as e:
            logging.error(f"Error connecting to MongoDB: {e}")
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    def create(self, data):
        """
        Insert a document into the collection.
        
        Args:
            data (dict): Document to insert. Must be a non-empty dictionary.
            
        Returns:
            bool: True if insertion succeeded, False otherwise.
        """
        # Input validation
        if not data:
            logging.warning("Create failed: No data provided")
            return False
        
        if not isinstance(data, dict):
            logging.warning(f"Create failed: Data must be a dictionary, got {type(data)}")
            return False
        
        if not data:
            logging.warning("Create failed: Data dictionary is empty")
            return False
        
        try:
            result = self.collection.insert_one(data)
            if result.inserted_id:
                logging.info(f"Document created successfully with ID: {result.inserted_id}")
                return True
            else:
                logging.warning("Create failed: No inserted ID returned")
                return False
        except Exception as e:
            logging.error(f"Error inserting document: {e}")
            return False
    
    def read(self, query=None):
        """
        Retrieve documents matching the query.
        
        Args:
            query (dict): MongoDB query filter. Defaults to empty dict (returns all).
            
        Returns:
            list: List of documents matching the query. Empty list if none found.
        """
        if query is None:
            query = {}
        
        if not isinstance(query, dict):
            logging.warning(f"Read failed: Query must be a dictionary, got {type(query)}")
            return []
        
        try:
            documents = list(self.collection.find(query))
            logging.info(f"Read query returned {len(documents)} documents")
            return documents
        except Exception as e:
            logging.error(f"Error reading documents: {e}")
            return []
    
    def update(self, query, new_values):
        """
        Update documents matching the query with new values.
        
        Args:
            query (dict): MongoDB query filter to find documents to update
            new_values (dict): New values to set on matching documents
            
        Returns:
            int: Number of documents modified. 0 if none or if error.
        """
        if not isinstance(query, dict):
            logging.warning(f"Update failed: Query must be a dictionary, got {type(query)}")
            return 0
        
        if not isinstance(new_values, dict):
            logging.warning(f"Update failed: new_values must be a dictionary, got {type(new_values)}")
            return 0
        
        if not new_values:
            logging.warning("Update failed: new_values dictionary is empty")
            return 0
        
        try:
            result = self.collection.update_many(query, {"$set": new_values})
            logging.info(f"Update completed: {result.modified_count} documents modified")
            return result.modified_count
        except Exception as e:
            logging.error(f"Error updating documents: {e}")
            return 0
    
    def delete(self, query):
        """
        Delete documents matching the query.
        
        Args:
            query (dict): MongoDB query filter to find documents to delete
            
        Returns:
            int: Number of documents deleted. 0 if none or if error.
        """
        if not isinstance(query, dict):
            logging.warning(f"Delete failed: Query must be a dictionary, got {type(query)}")
            return 0
        
        if not query:
            logging.warning("Delete called with empty query - this would delete ALL documents. Operation blocked.")
            return 0
        
        try:
            result = self.collection.delete_many(query)
            logging.info(f"Delete completed: {result.deleted_count} documents deleted")
            return result.deleted_count
        except Exception as e:
            logging.error(f"Error deleting documents: {e}")
            return 0
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")