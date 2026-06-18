"""
test_database_enhancements.py - Test script for database enhancements
Author: Manoj Chaudhary
Course: CS 499 Capstone - Milestone Four
Date: June 7th,2026

This script tests:
1. Schema validation enforcement
2. Audit logging functionality
3. Aggregation pipeline performance
"""

import logging
from database_enhanced import AnimalShelterDatabase

logging.basicConfig(level=logging.INFO)


def test_schema_validation():
    """Test that schema validation rejects invalid documents."""
    print("\n" + "=" * 60)
    print("TEST 1: Schema Validation")
    print("=" * 60)
    
    db = AnimalShelterDatabase()
    
    # Test valid document
    valid_doc = {
        "name": "TestDog",
        "breed": "Labrador Retriever",
        "age_upon_outcome_in_weeks": 104,
        "location_lat": 30.2672,
        "location_long": -97.7431,
        "animal_type": "Dog"
    }
    
    print("\nTesting valid document...")
    result = db.create(valid_doc, user="test_user")
    print(f"  Valid document accepted: {result}")
    
    # Test invalid document (missing required field)
    invalid_doc = {
        "name": "TestDog2",
        # missing "breed" field
        "age_upon_outcome_in_weeks": 104
    }
    
    print("\nTesting invalid document (missing breed)...")
    result = db.create(invalid_doc, user="test_user")
    print(f"  Invalid document rejected: {not result}")
    
    db.close()


def test_audit_logging():
    """Test that audit logs are created for operations."""
    print("\n" + "=" * 60)
    print("TEST 2: Audit Logging")
    print("=" * 60)
    
    db = AnimalShelterDatabase()
    
    # Perform operations
    db.create({"name": "AuditTest", "breed": "Test", "age_upon_outcome_in_weeks": 50}, user="test_user")
    db.read({"breed": "Labrador"}, user="test_user")
    db.update({"name": "AuditTest"}, {"age_upon_outcome_in_weeks": 60}, user="test_user")
    db.delete({"name": "AuditTest"}, user="test_user")
    
    # Retrieve audit logs
    logs = db.get_audit_logs(limit=10)
    print(f"\nAudit logs retrieved: {len(logs)}")
    
    for log in logs[:5]:
        print(f"  - {log.get('timestamp')}: {log.get('action')} by {log.get('user')}")
    
    db.close()


def test_aggregation_pipelines():
    """Test aggregation pipeline functionality."""
    print("\n" + "=" * 60)
    print("TEST 3: Aggregation Pipelines")
    print("=" * 60)
    
    db = AnimalShelterDatabase()
    
    # Test top breeds for Water Rescue
    print("\nTop breeds for Water Rescue:")
    results = db.get_top_breeds_for_rescue("Water Rescue", limit=5)
    for r in results:
        print(f"  - {r.get('breed')}: {r.get('count')} animals, avg age {r.get('average_age_weeks'):.1f} weeks")
    
    # Test summary statistics
    print("\nRescue statistics summary:")
    summary = db.get_rescue_statistics_summary()
    print(f"  Total unique breeds: {summary.get('total_unique_breeds', 'N/A')}")
    
    db.close()


def run_all_tests():
    """Run all database enhancement tests."""
    print("\n" + "=" * 70)
    print("DATABASE ENHANCEMENTS - TEST SUITE")
    print("=" * 70)
    
    try:
        test_schema_validation()
        test_audit_logging()
        test_aggregation_pipelines()
    except Exception as e:
        print(f"\nError during testing: {e}")
    
    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()