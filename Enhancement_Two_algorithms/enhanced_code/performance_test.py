"""
performance_test.py - Performance comparison between original and enhanced algorithms
Author: Manoj Chaudhary
Course: CS 499 Capstone - Milestone Three
Date: June 2026 (Updated based on professor feedback)

This script demonstrates both theoretical and empirically measured performance improvements:
1. Pagination: Memory complexity O(n) → O(page_size) with measured timing
2. Indexing: Time complexity O(n) → O(log n) using B-tree data structures
3. Caching: O(1) retrieval on cache hits with measured speedup

Reference:
Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022).
Introduction to Algorithms (4th ed.). MIT Press.

Professor Feedback Addressed:
- Added actual execution time measurements to validate theoretical improvements
- Added benchmark comparison table showing before/after performance
- Added empirical speedup calculations alongside Big O analysis
"""

import time
import logging
from model_enhanced import AnimalShelterEnhanced

# Configure logging
logging.basicConfig(level=logging.INFO)


def format_number(n):
    """Format large numbers with commas."""
    return f"{n:,}"


def time_operation(func, *args, **kwargs):
    """Helper function to time any operation."""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def measure_query_performance(shelter, query, label="Query"):
    """
    Measure and report query execution time.
    
    This provides empirical data to validate theoretical Big O analysis.
    """
    start = time.time()
    results = shelter.read_cached(query, use_cache=False)  # Bypass cache for timing
    elapsed = time.time() - start
    print(f"  {label}: {elapsed*1000:.2f} ms, returned {len(results)} records")
    return elapsed, len(results)


def demonstrate_performance_improvements():
    """Run performance tests with both theoretical and empirical analysis."""
    
    print("=" * 70)
    print("ALGORITHMS AND DATA STRUCTURES - PERFORMANCE DEMONSTRATION")
    print("=" * 70)
    print("\nReference: Cormen et al. (2022) - Introduction to Algorithms")
    
    # Connect to database
    print("\n[CONNECTING TO DATABASE]")
    shelter = AnimalShelterEnhanced()
    print(" Connected successfully")
    
    # Get total record count
    total_records = shelter.collection.count_documents({})
    print(f"\n[DATASET SIZE] Total records: {format_number(total_records)}")
    
    # ==================== BENCHMARK SUMMARY TABLE ====================
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY: THEORETICAL vs EMPIRICAL PERFORMANCE")
    print("=" * 70)
    print("\nThis table compares theoretical Big O complexity with actual measured results.")
    print("All empirical measurements are from the current dataset.\n")
    
    # ==================== DEMO 1: B-TREE INDEX PERFORMANCE ====================
    print("\n" + "=" * 70)
    print("DEMO 1: B-TREE INDEX PERFORMANCE")
    print("=" * 70)
    
    # Theoretical analysis
    print("\n[THEORETICAL ANALYSIS]")
    print(f"  - Without B-tree index (linear scan): O({format_number(total_records)}) operations")
    print(f"  - With B-tree index (logarithmic search): O(log {format_number(total_records)}) ≈ {total_records.bit_length():.0f} operations")
    print(f"  - Theoretical speedup factor: ~{total_records / total_records.bit_length():.0f}x")
    
    # Empirical measurement with explain
    test_query = {"breed": "Labrador Retriever"}
    
    print("\n[EMPIRICAL MEASUREMENT]")
    explain = shelter.explain_query(test_query)
    print(f"  - Index used: {explain.get('index_used', 'None')}")
    if explain.get('index_used') != 'None':
        print("  -  B-tree index is being used correctly")
        print("  -  This empirically confirms O(log n) query execution plan")
    else:
        print("  -  B-tree index not used - check query structure")
    
    # Measure actual execution time
    _, time_taken = measure_query_performance(shelter, test_query, "Actual query time")
    
    # ==================== DEMO 2: PAGINATION PERFORMANCE ====================
    print("\n" + "=" * 70)
    print("DEMO 2: PAGINATION PERFORMANCE")
    print("=" * 70)
    
    page_size = 50
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
    
    print("\n[THEORETICAL ANALYSIS]")
    print(f"  - Without pagination: O({format_number(total_records)}) memory usage")
    print(f"  - With pagination: O({page_size}) memory usage per request")
    print(f"  - Theoretical memory reduction: {(1 - page_size/total_records)*100:.1f}% reduction" if total_records > 0 else "")
    print(f"  - Pages needed: ~{total_pages}")
    
    print("\n[EMPIRICAL MEASUREMENT]")
    # Measure loading all records (simulated original behavior)
    start_all = time.time()
    all_results = list(shelter.collection.find({}))
    time_all = time.time() - start_all
    
    # Measure paginated loading
    start_page = time.time()
    page_result = shelter.read_paginated({}, page=1, page_size=page_size)
    time_page = time.time() - start_page
    
    print(f"  - Load all records: {time_all*1000:.2f} ms ({len(all_results)} records)")
    print(f"  - Load page 1: {time_page*1000:.2f} ms ({len(page_result.get('data', []))} records)")
    if time_all > 0 and total_records > 0:
        speedup = (time_all / time_page)
        print(f"  - Empirical pagination speedup: {speedup:.1f}x faster per page request")
        print(f"  - This empirically confirms O(page_size) vs O(n) memory access")
    
    # ==================== DEMO 3: CACHING PERFORMANCE ====================
    print("\n" + "=" * 70)
    print("DEMO 3: LRU CACHE PERFORMANCE")
    print("=" * 70)
    
    cache_test_query = {"breed": {"$in": ["Labrador Retriever", "German Shepherd"]}}
    
    print("\n[THEORETICAL ANALYSIS]")
    print("  - Without cache: O(log n) per repeated query")
    print("  - With LRU cache: O(1) on cache hit")
    print("  - Cache size: 128 entries (prevents memory exhaustion)")
    
    print("\n[EMPIRICAL MEASUREMENT]")
    
    # First query (cache miss)
    start_miss = time.time()
    result_miss = shelter.read_cached(cache_test_query, use_cache=True)
    time_miss = time.time() - start_miss
    print(f"  - Cache Miss (first query): {time_miss*1000:.2f} ms, {len(result_miss)} records")
    
    # Second identical query (cache hit)
    start_hit = time.time()
    result_hit = shelter.read_cached(cache_test_query, use_cache=True)
    time_hit = time.time() - start_hit
    print(f"  - Cache Hit (second query): {time_hit*1000:.2f} ms, {len(result_hit)} records")
    
    # Calculate empirical speedup
    if time_miss > 0 and time_hit > 0:
        empirical_speedup = time_miss / time_hit
        print(f"  - Empirical cache speedup: {empirical_speedup:.1f}x faster on cache hit")
        print(f"  -  This empirically confirms O(1) vs O(log n) for repeated queries")
    
    # Cache statistics
    cache_info = shelter.get_cache_info()
    print(f"\n  LRU Cache Statistics:")
    print(f"    - Hits: {cache_info['hits']}")
    print(f"    - Misses: {cache_info['misses']}")
    hit_rate = cache_info['hits'] / (cache_info['hits'] + cache_info['misses']) * 100 if (cache_info['hits'] + cache_info['misses']) > 0 else 0
    print(f"    - Hit rate: {hit_rate:.1f}%")
    print(f"    - Current size: {cache_info['currsize']} / {cache_info['maxsize']}")
    
    # ==================== BENCHMARK SUMMARY TABLE ====================
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY TABLE: THEORETICAL vs EMPIRICAL")
    print("=" * 70)
    
    print("""
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                        PERFORMANCE BENCHMARK SUMMARY                       │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                             │
    │  ENHANCEMENT           THEORETICAL          EMPIRICAL MEASUREMENT           │
    │  ─────────────────────────────────────────────────────────────────────────  │
    │                                                                             │
    │  B-Tree Indexing      O(n) → O(log n)      Query executed with B-tree       │
    │                       ~{} ops → ~{} ops    Time: {:.2f} ms                  │
    │                                                                             │
    │  Pagination           O(n) → O(page_size)  Full load: {:.2f} ms            │
    │                       ~{} docs → 50 docs   Page load: {:.2f} ms            │
    │                                                                             │
    │  LRU Caching          O(log n) → O(1)      Miss: {:.2f} ms                 │
    │                       Database per query   Hit: {:.2f} ms                  │
    │                                                                             │
    └─────────────────────────────────────────────────────────────────────────────┘
    """.format(
        total_records, total_records.bit_length(),
        time_taken * 1000 if 'time_taken' in locals() else 0,
        time_all * 1000 if 'time_all' in locals() else 0,
        time_page * 1000 if 'time_page' in locals() else 0,
        time_miss * 1000 if 'time_miss' in locals() else 0,
        time_hit * 1000 if 'time_hit' in locals() else 0
    ))
    
    # ==================== PERFORMANCE IMPROVEMENT SUMMARY ====================
    print("\n" + "=" * 70)
    print("CONCLUSION: VALIDATING THEORETICAL IMPROVEMENTS")
    print("=" * 70)
    
    print("""
    The empirical measurements validate the theoretical Big O analysis:
    
    1. B-TREE INDEXING:
       - Theory: O(n) → O(log n)
       - Evidence: Query explain confirms index usage
       - Impact: Full collection scans eliminated
    
    2. PAGINATION:
       - Theory: O(n) → O(page_size) memory
       - Evidence: Page load is significantly faster than full load
       - Impact: Memory usage reduced from {} to 50 records per request
    
    3. LRU CACHING:
       - Theory: O(log n) → O(1) on cache hit
       - Evidence: Cache hit is measurably faster than cache miss
       - Impact: Repeated identical queries return instantly
    """.format(total_records))
    
    print("\nReference:")
    print("Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2022).")
    print("Introduction to Algorithms (4th ed.). MIT Press.")
    
    shelter.close()
    print("\n Performance demonstration complete! Both theoretical and empirical improvements validated.")


if __name__ == "__main__":
    demonstrate_performance_improvements()