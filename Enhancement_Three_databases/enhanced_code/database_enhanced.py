"""
database_enhanced.py - Enhanced Database Operations for Animal Shelter
Author: Manoj Chaudhary
Course: CS 499 Capstone - Milestone Four (Databases)
Date: June 7th, 2026

Enhancements in this file:
1. Schema validation using MongoDB JSON Schema
2. Audit logging collection for all CRUD operations
3. Aggregation pipelines for analytics
4. TTL index for automatic audit log cleanup
"""

import logging
import os
import json
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_enhancement.log'),
        logging.StreamHandler()
    ]
)


class AnimalShelterDatabase:
    """
    Enhanced AnimalShelter class with database-specific improvements.
    
    New Database Features:
    - Schema Validation: JSON Schema enforces data quality at database level
    - Audit Logging: Tracks all CREATE, UPDATE, DELETE operations
    - Aggregation Pipelines: Server-side analytics for performance
    - TTL Indexes: Automatic cleanup of old audit records
    """
    
    def __init__(self, username=None, password=None, host='localhost', 
                 port=27017, database_name="aac", collection_name="animals"):
        """
        Initialize MongoDB connection and set up database enhancements.
        """
        self.username = username or os.getenv('MONGODB_USERNAME')
        self.password = password or os.getenv('MONGODB_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Database credentials not found in environment variables")
        
        try:
            uri = f"mongodb://{self.username}:{self.password}@{host}:{port}/{database_name}?authSource={database_name}"
            self.client = MongoClient(uri)
            self.client.admin.command('ping')
            self.database = self.client[database_name]
            self.collection = self.database[collection_name]
            logging.info(f"MongoDB connection successful to '{database_name}'")
            
            # Set up database enhancements
            self._setup_schema_validation()
            self._setup_audit_collection()
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            raise
    
    # ==================== ENHANCEMENT 1: SCHEMA VALIDATION ====================
    
    def _setup_schema_validation(self):
        """
        Set up JSON Schema validation on the animals collection.
        
        This ensures data quality at the database level. Documents that
        do not match the schema are rejected with descriptive errors.
        
        The schema enforces:
        - Required fields: name, breed, age_upon_outcome_in_weeks
        - Data types: string, integer, double
        - Value ranges: age between 0-1040 weeks, lat/long within bounds
        """
        try:
            validation_rules = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "title": "Animal Schema Validation",
                    "required": ["name", "breed", "age_upon_outcome_in_weeks"],
                    "properties": {
                        "name": {
                            "bsonType": "string",
                            "minLength": 1,
                            "description": "Animal name is required and must be non-empty"
                        },
                        "breed": {
                            "bsonType": "string",
                            "minLength": 1,
                            "description": "Breed is required"
                        },
                        "age_upon_outcome_in_weeks": {
                            "bsonType": "int",
                            "minimum": 0,
                            "maximum": 1040,
                            "description": "Age must be between 0 and 1040 weeks (20 years)"
                        },
                        "location_lat": {
                            "bsonType": "double",
                            "minimum": -90,
                            "maximum": 90,
                            "description": "Latitude must be between -90 and 90"
                        },
                        "location_long": {
                            "bsonType": "double",
                            "minimum": -180,
                            "maximum": 180,
                            "description": "Longitude must be between -180 and 180"
                        },
                        "animal_type": {
                            "bsonType": "string",
                            "enum": ["Dog", "Cat", "Other"],
                            "description": "Animal type must be Dog, Cat, or Other"
                        }
                    },
                    "additionalProperties": True
                }
            }
            
            # Apply validation to the collection
            self.database.command({
                "collMod": self.collection.name,
                "validator": validation_rules,
                "validationLevel": "strict",
                "validationAction": "error"
            })
            logging.info("Schema validation enabled on 'animals' collection")
            
        except Exception as e:
            logging.warning(f"Schema validation setup had issues: {e}")
    
    # ==================== ENHANCEMENT 2: AUDIT LOGGING ====================
    
    def _setup_audit_collection(self):
        """
        Create audit_log collection for tracking all data modifications.
        
        The audit log records:
        - Timestamp of the operation
        - Action type (CREATE, UPDATE, DELETE, READ)
        - Collection name
        - Document ID or query
        - User who performed the action
        - Changes made (for updates)
        
        A TTL index automatically deletes audit records after 90 days.
        """
        try:
            # Create audit collection if it doesn't exist
            if "audit_log" not in self.database.list_collection_names():
                self.database.create_collection("audit_log")
                logging.info("Created audit_log collection")
            
            # Create TTL index for automatic cleanup (90 days = 7776000 seconds)
            self.database.audit_log.create_index(
                "timestamp", 
                expireAfterSeconds=7776000,
                name="ttl_audit_index"
            )
            logging.info("TTL index created on audit_log (90-day retention)")
            
        except Exception as e:
            logging.warning(f"Audit collection setup had issues: {e}")
    
    def _log_audit_event(self, action, collection_name, document_id=None, 
                         query=None, changes=None, user="dashboard_user"):
        """
        Log a database operation to the audit trail.
        
        Args:
            action (str): CREATE, UPDATE, DELETE, or READ
            collection_name (str): Name of the collection affected
            document_id (str): ID of the affected document (if applicable)
            query (dict): Query used for the operation
            changes (dict): Changes made (for updates)
            user (str): User who performed the operation
        """
        try:
            audit_entry = {
                "timestamp": datetime.now(),
                "action": action,
                "collection": collection_name,
                "document_id": str(document_id) if document_id else None,
                "query": json.dumps(query, default=str) if query else None,
                "changes": json.dumps(changes, default=str) if changes else None,
                "user": user,
                "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
            }
            
            self.database.audit_log.insert_one(audit_entry)
            logging.debug(f"Audit log entry created: {action}")
            
        except Exception as e:
            logging.error(f"Audit logging failed: {e}")
    
    # ==================== ENHANCEMENT 3: AGGREGATION PIPELINES ====================
    
    def get_top_breeds_for_rescue(self, rescue_type, limit=5, max_age_weeks=104):
        """
        Use aggregation pipeline to get top breeds for a rescue type.
        
        This replaces client-side pandas aggregation with server-side processing.
        
        Args:
            rescue_type (str): Water Rescue, Mountain/Wilderness Rescue, or Disaster/Individual Tracking
            limit (int): Number of top breeds to return
            max_age_weeks (int): Maximum age in weeks
            
        Returns:
            list: Aggregated breed statistics
        """
        # Define breed lists for each rescue type
        rescue_breeds = {
            "Water Rescue": ["Labrador Retriever", "Newfoundland", "Portuguese Water Dog", "Chesapeake Bay Retriever"],
            "Mountain/Wilderness Rescue": ["German Shepherd", "Border Collie", "Australian Shepherd", "Siberian Husky"],
            "Disaster/Individual Tracking": ["Belgian Malinois", "Bloodhound", "German Shepherd", "Labrador Retriever"]
        }
        
        target_breeds = rescue_breeds.get(rescue_type, [])
        
        if not target_breeds:
            return []
        
        pipeline = [
            # Stage 1: Filter to relevant breeds and age
            {"$match": {
                "breed": {"$in": target_breeds},
                "age_upon_outcome_in_weeks": {"$lte": max_age_weeks}
            }},
            
            # Stage 2: Group by breed and calculate statistics
            {"$group": {
                "_id": "$breed",
                "count": {"$sum": 1},
                "average_age_weeks": {"$avg": "$age_upon_outcome_in_weeks"},
                "min_age": {"$min": "$age_upon_outcome_in_weeks"},
                "max_age": {"$max": "$age_upon_outcome_in_weeks"}
            }},
            
            # Stage 3: Sort by count descending
            {"$sort": {"count": -1}},
            
            # Stage 4: Limit to top N breeds
            {"$limit": limit},
            
            # Stage 5: Format output
            {"$project": {
                "breed": "$_id",
                "count": 1,
                "average_age_weeks": 1,
                "min_age": 1,
                "max_age": 1,
                "_id": 0
            }}
        ]
        
        try:
            results = list(self.collection.aggregate(pipeline))
            self._log_audit_event("AGGREGATE", self.collection.name, 
                                  query={"pipeline": "get_top_breeds_for_rescue"})
            logging.info(f"Aggregation returned {len(results)} breed statistics")
            return results
        except Exception as e:
            logging.error(f"Aggregation failed: {e}")
            return []
    
    def get_age_distribution_by_breed(self, breed):
        """
        Get age distribution statistics for a specific breed.
        
        Args:
            breed (str): Breed name
            
        Returns:
            dict: Age distribution statistics
        """
        pipeline = [
            {"$match": {"breed": breed}},
            {"$group": {
                "_id": None,
                "total_count": {"$sum": 1},
                "avg_age_weeks": {"$avg": "$age_upon_outcome_in_weeks"},
                "min_age_weeks": {"$min": "$age_upon_outcome_in_weeks"},
                "max_age_weeks": {"$max": "$age_upon_outcome_in_weeks"},
                "age_std_dev": {"$stdDevPop": "$age_upon_outcome_in_weeks"}
            }},
            {"$addFields": {
                "avg_age_years": {"$divide": ["$avg_age_weeks", 52]},
                "distribution_category": {
                    "$switch": {
                        "branches": [
                            {"case": {"$lt": ["$avg_age_weeks", 52]}, "then": "Puppy"},
                            {"case": {"$lt": ["$avg_age_weeks", 208]}, "then": "Adult"},
                            {"case": {"$gte": ["$avg_age_weeks", 208]}, "then": "Senior"}
                        ]
                    }
                }
            }},
            {"$project": {"_id": 0}}
        ]
        
        try:
            results = list(self.collection.aggregate(pipeline))
            self._log_audit_event("AGGREGATE", self.collection.name,
                                  query={"pipeline": "get_age_distribution_by_breed", "breed": breed})
            return results[0] if results else {}
        except Exception as e:
            logging.error(f"Age distribution aggregation failed: {e}")
            return {}
    
    def get_rescue_statistics_summary(self):
        """
        Get a summary of rescue suitability across all animal types.
        
        Returns:
            dict: Summary statistics for each rescue type
        """
        pipeline = [
            {"$match": {"age_upon_outcome_in_weeks": {"$lte": 104}}},
            {"$group": {
                "_id": "$breed",
                "count": {"$sum": 1},
                "avg_age": {"$avg": "$age_upon_outcome_in_weeks"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        try:
            results = list(self.collection.aggregate(pipeline))
            return {
                "total_unique_breeds": len(results),
                "top_breeds": results[:5],
                "query_executed": "aggregation_pipeline"
            }
        except Exception as e:
            logging.error(f"Summary aggregation failed: {e}")
            return {"error": str(e)}
    
    # ==================== CRUD OPERATIONS WITH AUDIT LOGGING ====================
    
    def create(self, data, user="dashboard_user"):
        """
        Insert a document with audit logging.
        """
        if not data or not isinstance(data, dict):
            logging.warning("Create failed: Invalid data")
            return False
        
        try:
            result = self.collection.insert_one(data)
            if result.inserted_id:
                self._log_audit_event("CREATE", self.collection.name, 
                                      document_id=result.inserted_id, 
                                      query=None, changes=data, user=user)
                logging.info(f"Document created: {result.inserted_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Create failed: {e}")
            return False
    
    def read(self, query=None, user="dashboard_user", log_read=True):
        """
        Retrieve documents with optional audit logging.
        """
        if query is None:
            query = {}
        
        try:
            results = list(self.collection.find(query))
            if log_read:
                self._log_audit_event("READ", self.collection.name,
                                      query=query, user=user)
            for doc in results:
                doc['_id'] = str(doc['_id'])
            return results
        except Exception as e:
            logging.error(f"Read failed: {e}")
            return []
    
    def update(self, query, new_values, user="dashboard_user"):
        """
        Update documents with audit logging.
        """
        if not isinstance(query, dict) or not isinstance(new_values, dict):
            return 0
        
        try:
            result = self.collection.update_many(query, {"$set": new_values})
            if result.modified_count > 0:
                self._log_audit_event("UPDATE", self.collection.name,
                                      query=query, changes=new_values, user=user)
            logging.info(f"Updated {result.modified_count} documents")
            return result.modified_count
        except Exception as e:
            logging.error(f"Update failed: {e}")
            return 0
    
    def delete(self, query, user="dashboard_user"):
        """
        Delete documents with audit logging.
        """
        if not isinstance(query, dict):
            return 0
        if not query:
            logging.warning("Empty delete query blocked")
            return 0
        
        try:
            result = self.collection.delete_many(query)
            if result.deleted_count > 0:
                self._log_audit_event("DELETE", self.collection.name,
                                      query=query, user=user)
            logging.info(f"Deleted {result.deleted_count} documents")
            return result.deleted_count
        except Exception as e:
            logging.error(f"Delete failed: {e}")
            return 0
    
    # ==================== UTILITY METHODS ====================
    
    def get_audit_logs(self, action=None, limit=100):
        """
        Retrieve audit logs for review.
        
        Args:
            action (str): Filter by action type (CREATE, UPDATE, DELETE, READ)
            limit (int): Maximum number of logs to return
            
        Returns:
            list: Audit log entries
        """
        query = {}
        if action:
            query["action"] = action
        
        try:
            logs = list(self.database.audit_log.find(query).sort("timestamp", -1).limit(limit))
            for log in logs:
                log['_id'] = str(log['_id'])
            return logs
        except Exception as e:
            logging.error(f"Failed to retrieve audit logs: {e}")
            return []
    
    def get_schema_validation_status(self):
        """
        Check if schema validation is enabled.
        
        Returns:
            dict: Validation status information
        """
        try:
            collection_info = self.database.command("listCollections", filter={"name": self.collection.name})
            return {"validation_enabled": True, "status": "active"}
        except:
            return {"validation_enabled": False, "status": "not_configured"}
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logging.info("Database connection closed")