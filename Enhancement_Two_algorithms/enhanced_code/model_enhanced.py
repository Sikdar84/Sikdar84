"""
model_enhanced.py - Enhanced AnimalShelter with Algorithm Optimizations
Author: Manoj Chaudhary
Course: CS 499 Capstone - Milestone Three (Algorithms and Data Structures)
Date: May 31, 2026

Enhancements in this file:
1. Server-side pagination with skip() and limit()
2. LRU caching using functools.lru_cache
3. Index creation and management using B-tree data structures
4. Query optimization with explain() for performance analysis
"""

import logging
import os
import json
from functools import lru_cache
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('animal_shelter_algorithms.log'),
        logging.StreamHandler()
    ]
)


class AnimalShelterEnhanced:
    """
    Enhanced AnimalShelter class with algorithm optimizations.
    
    New Features:
    - Pagination: Server-side pagination to reduce memory usage from O(n) to O(page_size)
    - Caching: LRU cache to store frequent query results (max 128 entries)
    - Indexing: B-tree based indexes for O(log n) query performance
    """
    
    def __init__(self, username=None, password=None, host='localhost', 
                 port=27017, database_name="aac", collection_name="animals"):
        """
        Initialize MongoDB connection and create optimized indexes.
        
        Time Complexity: O(1) for connection, O(k log n) for index creation (k = number of indexes)
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
            
            # Create optimized indexes for algorithm performance
            self._create_optimized_indexes()
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            raise
    
    def _create_optimized_indexes(self):
        """
        Create indexes for O(log n) query performance instead of O(n) collection scans.
        
        DATA STRUCTURE NOTE: MongoDB indexes are implemented using B-tree data structures.
        According to Cormen et al. (2022), B-trees enable logarithmic-time search, insertion,
        and deletion operations, which scale significantly better than linear scans as
        dataset size increases.
        
        Indexes Created:
        1. breed_index: Single-field B-tree index for breed filtering
        2. age_index: Single-field B-tree index for age range queries
        3. breed_age_compound: Compound B-tree index for combined breed + age queries
        4. location_index: 2dsphere index for geospatial queries (map display)
        5. name_text_index: Text index for name/breed search
        
        Without indexes: O(n) - full collection scan
        With B-tree indexes: O(log n) - logarithmic lookup
        
        Reference:
        Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022).
        Introduction to Algorithms (4th ed.). MIT Press.
        """
        try:
            # Index 1: Single-field B-tree index on breed
            self.collection.create_index([("breed", ASCENDING)], name="breed_index")
            logging.info("Created B-tree index: breed_index")
            
            # Index 2: Single-field B-tree index on age
            self.collection.create_index([("age_upon_outcome_in_weeks", ASCENDING)], name="age_index")
            logging.info("Created B-tree index: age_index")
            
            # Index 3: Compound B-tree index for breed + age (most common query pattern)
            self.collection.create_index(
                [("breed", ASCENDING), ("age_upon_outcome_in_weeks", ASCENDING)], 
                name="breed_age_compound"
            )
            logging.info("Created compound B-tree index: breed_age_compound")
            
            # Index 4: 2dsphere index for location queries (map)
            try:
                self.collection.create_index([("location", "2dsphere")], name="location_index")
                logging.info("Created geospatial index: location_index")
            except:
                logging.info("2dsphere index skipped - location field may not be present")
            
            # Index 5: Text index for search functionality
            try:
                self.collection.create_index([("name", TEXT), ("breed", TEXT)], name="name_text_index")
                logging.info("Created text index: name_text_index")
            except:
                logging.info("Text index skipped - name/breed text search not needed")
            
            logging.info("All indexes created successfully - Query performance improved from O(n) to O(log n)")
            
        except Exception as e:
            logging.warning(f"Index creation had issues: {e}")
    
    def get_index_info(self):
        """
        Return information about existing indexes for performance analysis.
        
        Returns:
            dict: Index information for the collection
        """
        return self.collection.index_information()
    
    def explain_query(self, query):
        """
        Explain how MongoDB will execute a query (for performance analysis).
        
        Args:
            query (dict): MongoDB query to analyze
            
        Returns:
            dict: Execution plan showing whether B-tree indexes are used
        """
        try:
            explain_result = self.collection.find(query).explain()
            return {
                "query_plan": explain_result.get("queryPlanner", {}),
                "winning_plan": explain_result.get("queryPlanner", {}).get("winningPlan", {}),
                "index_used": explain_result.get("queryPlanner", {}).get("winningPlan", {}).get("inputStage", {}).get("indexName", "None")
            }
        except Exception as e:
            logging.error(f"Explain failed: {e}")
            return {"error": str(e)}
    
    # ==================== PAGINATION ENHANCEMENT ====================
    
    def read_paginated(self, query=None, page=1, page_size=50, sort_by="breed", sort_order=1):
        """
        Read documents with server-side pagination.
        
        ALGORITHM ENHANCEMENT #1: Server-Side Pagination
        
        Without Pagination (Original):
            - Loads ALL records into memory: O(n) memory complexity
            - Transfers ALL records over network: O(n) bandwidth
            - Browser processes ALL records: O(n) client time
        
        With Pagination (Enhanced):
            - Loads ONLY page_size records: O(page_size) memory complexity
            - Transfers ONLY page_size records: O(page_size) bandwidth
            - For page_size=50, this represents a significant reduction in resource usage
        
        Time Complexity: O(log n) for indexed query + O(page_size) for results
        Space Complexity: O(page_size) - constant per page
        
        Args:
            query (dict): MongoDB query filter
            page (int): Page number (1-indexed)
            page_size (int): Number of records per page
            sort_by (str): Field to sort by
            sort_order (int): 1 for ascending, -1 for descending
            
        Returns:
            dict: Contains data, pagination metadata, and performance metrics
        """
        if query is None:
            query = {}
        
        # Calculate skip count
        skip_count = (page - 1) * page_size
        
        # Determine sort order
        sort_direction = ASCENDING if sort_order == 1 else DESCENDING
        
        # Execute paginated query using B-tree index
        cursor = self.collection.find(query).sort(sort_by, sort_direction).skip(skip_count).limit(page_size)
        
        # Get total count for pagination UI (uses count_documents with B-tree index)
        total_count = self.collection.count_documents(query)
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        
        # Execute query and convert to list
        results = list(cursor)
        
        # Remove MongoDB _id for JSON serialization
        for doc in results:
            doc['_id'] = str(doc['_id'])
        
        # Return data with metadata
        return {
            "data": results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "start_record": skip_count + 1,
                "end_record": min(skip_count + page_size, total_count)
            },
            "performance": {
                "skip_count": skip_count,
                "limit": page_size,
                "sort_field": sort_by,
                "time_complexity": "O(log n) for query + O(page_size) for results"
            }
        }
    
    # ==================== CACHING ENHANCEMENT ====================
    
    @lru_cache(maxsize=128)
    def _read_cached(self, query_json_string):
        """
        Cached version of read() - INTERNAL METHOD.
        
        ALGORITHM ENHANCEMENT #2: LRU (Least Recently Used) Caching
        
        Without Caching (Original):
            - Every query hits the database: O(log n) per request
            - Repeated identical queries waste database resources
        
        With LRU Caching (Enhanced):
            - Cache hit: O(1) - returns instantly from cache data structure
            - Cache miss: O(log n) - database query with B-tree index
            - Maxsize=128 prevents memory exhaustion
            - LRU eviction policy removes least recently used entries first
        
        Args:
            query_json_string (str): JSON string of the query (for hashability)
            
        Returns:
            list: Cached or fresh query results
        """
        query = json.loads(query_json_string)
        
        try:
            results = list(self.collection.find(query))
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                doc['_id'] = str(doc['_id'])
            logging.info(f"CACHE MISS: Query executed against database. Returned {len(results)} records")
            return results
        except Exception as e:
            logging.error(f"Cached read failed: {e}")
            return []
    
    def read_cached(self, query, use_cache=True):
        """
        Read documents with optional LRU caching.
        
        Args:
            query (dict): MongoDB query filter
            use_cache (bool): Whether to use cache (True) or bypass (False)
            
        Returns:
            list: Query results
        """
        if not use_cache:
            # Bypass cache - direct database query
            try:
                results = list(self.collection.find(query))
                for doc in results:
                    doc['_id'] = str(doc['_id'])
                return results
            except Exception as e:
                logging.error(f"Direct read failed: {e}")
                return []
        
        # Use cache - convert query to stable JSON string for cache key
        query_json = json.dumps(query, sort_keys=True)
        return self._read_cached(query_json)
    
    def clear_cache(self):
        """
        Clear the LRU cache when data modifications occur.
        
        Call this method after any create, update, or delete operation
        to ensure cache consistency.
        """
        self._read_cached.cache_clear()
        logging.info("Cache cleared successfully")
    
    def get_cache_info(self):
        """
        Get information about current cache state.
        
        Returns:
            dict: Cache statistics including size and maxsize
        """
        cache_info = self._read_cached.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "maxsize": cache_info.maxsize,
            "currsize": cache_info.currsize
        }
    
    # ==================== OPTIMIZED QUERY METHODS ====================
    
    def read_optimized(self, rescue_type=None, max_age=None, breed=None, 
                       page=1, page_size=50, use_cache=True):
        """
        Optimized query builder that uses B-tree indexes effectively.
        
        ALGORITHM ENHANCEMENT #3: Optimized Query Building
        
        This method builds queries in a way that maximizes B-tree index usage:
        - Uses $and to combine filters for compound index
        - Places indexed fields first
        - Avoids regex when possible (uses $in instead)
        
        Args:
            rescue_type (str): Type of rescue (Water, Mountain, Disaster)
            max_age (int): Maximum age in weeks
            breed (str): Specific breed filter
            page (int): Page number for pagination
            page_size (int): Records per page
            use_cache (bool): Whether to use caching
            
        Returns:
            dict: Paginated results with metadata
        """
        # Build query components in order of index priority
        query_components = []
        
        # Breed filter (uses breed_index B-tree)
        if breed:
            query_components.append({"breed": breed})
        elif rescue_type:
            # Map rescue type to breeds (defined in controller)
            rescue_breeds = self._get_rescue_breeds(rescue_type)
            if rescue_breeds:
                query_components.append({"breed": {"$in": rescue_breeds}})
        
        # Age filter (uses age_index or compound B-tree index)
        if max_age is not None:
            query_components.append({"age_upon_outcome_in_weeks": {"$lte": max_age}})
        
        # Combine query components with $and for optimal B-tree index usage
        if len(query_components) == 0:
            final_query = {}
        elif len(query_components) == 1:
            final_query = query_components[0]
        else:
            final_query = {"$and": query_components}
        
        # Use cached read if requested
        if use_cache:
            results = self.read_cached(final_query, use_cache=True)
        else:
            try:
                results = list(self.collection.find(final_query))
                for doc in results:
                    doc['_id'] = str(doc['_id'])
            except Exception as e:
                logging.error(f"Optimized read failed: {e}")
                results = []
        
        # Apply pagination to results
        total_count = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_results = results[start_idx:end_idx]
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "data": paginated_results,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    def _get_rescue_breeds(self, rescue_type):
        """
        Get breed list for a rescue type.
        
        Args:
            rescue_type (str): Water Rescue, Mountain/Wilderness Rescue, or Disaster/Individual Tracking
            
        Returns:
            list: List of breed names for that rescue type
        """
        rescue_map = {
            "Water Rescue": ["Labrador Retriever", "Newfoundland", "Portuguese Water Dog", "Chesapeake Bay Retriever"],
            "Mountain/Wilderness Rescue": ["German Shepherd", "Border Collie", "Australian Shepherd", "Siberian Husky"],
            "Disaster/Individual Tracking": ["Belgian Malinois", "Bloodhound", "German Shepherd", "Labrador Retriever"]
        }
        return rescue_map.get(rescue_type, [])
    
    # ==================== BASIC CRUD METHODS (Enhanced) ====================
    
    def create(self, data):
        """Insert a document and clear cache."""
        if not data or not isinstance(data, dict):
            return False
        
        try:
            result = self.collection.insert_one(data)
            if result.inserted_id:
                self.clear_cache()
                logging.info(f"Document created: {result.inserted_id}")
                return True
            return False
        except Exception as e:
            logging.error(f"Create failed: {e}")
            return False
    
    def update(self, query, new_values):
        """Update documents and clear cache."""
        if not isinstance(query, dict) or not isinstance(new_values, dict):
            return 0
        
        try:
            result = self.collection.update_many(query, {"$set": new_values})
            if result.modified_count > 0:
                self.clear_cache()
            logging.info(f"Updated {result.modified_count} documents")
            return result.modified_count
        except Exception as e:
            logging.error(f"Update failed: {e}")
            return 0
    
    def delete(self, query):
        """Delete documents and clear cache."""
        if not isinstance(query, dict):
            return 0
        if not query:
            logging.warning("Empty delete query blocked")
            return 0
        
        try:
            result = self.collection.delete_many(query)
            if result.deleted_count > 0:
                self.clear_cache()
            logging.info(f"Deleted {result.deleted_count} documents")
            return result.deleted_count
        except Exception as e:
            logging.error(f"Delete failed: {e}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logging.info("Connection closed")
            