"""Phase 4 unit tests -- run with: python tests/test_filter_engine.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.filter.engine import filter_with_fallback
from src.models.preferences import UserPreferences

passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        failed += 1

print("\n--- Phase 4: Filter Engine Unit Tests ---\n")

# Mock DataFrame for testing
mock_data = {
    "name": ["A", "B", "C", "D", "E"],
    "location": ["bangalore", "bangalore", "bangalore", "delhi", "bangalore"],
    "budget_category": ["low", "low", "medium", "low", "low"],
    "cuisine": ["italian", "italian", "italian", "italian", "chinese"],
    "rating": [4.5, 4.2, 4.8, 4.0, 3.5],
    "votes": [100, 50, 200, 10, 5],
    "avg_cost_for_two": [300, 400, 1000, 200, 250],
}
df = pd.DataFrame(mock_data)

# Test 1: Strict filter returns correct results (no fallback)
prefs_strict = UserPreferences(
    location="bangalore",
    budget="low",
    cuisine="italian",
    min_rating=4.0,
    extras=""
)
# Matches A and B
res = filter_with_fallback(df, prefs_strict)
# But wait, Fallback threshold is 3 in engine.py!
# If fallback threshold is 3, and only A and B match, it will trigger fallback!
# Let's adjust mock_data to have at least 3 exact matches.
df.loc[5] = ["F", "bangalore", "low", "italian", 4.1, 30, 350]

res = filter_with_fallback(df, prefs_strict)
check("Strict filter returns exact matches without fallback", 
      res.fallback_level == 0 and len(res.candidates) == 3, 
      f"got level {res.fallback_level}, {len(res.candidates)} matches")

# Test 2: Fallback Level 1 (Drop Cuisine)
# Let's look for "mexican" where there are none, but we have enough other bangalore low-budget restaurants.
prefs_level1 = UserPreferences(
    location="bangalore",
    budget="low",
    cuisine="mexican",
    min_rating=3.0,
    extras=""
)
# Level 1 fallback drops cuisine, so it will match A, B, E, F (4 results >= 3)
res_l1 = filter_with_fallback(df, prefs_level1)
check("Fallback Level 1 drops cuisine filter", 
      res_l1.fallback_level == 1 and len(res_l1.candidates) >= 3)

# Test 3: Fallback Level 2 (Drop Budget)
# Look for 'mexican' and 'high' budget in bangalore (none exist).
# Drop cuisine -> still 0 'high'. Drop budget -> matches A, B, C, E, F (5 results >= 3)
prefs_level2 = UserPreferences(
    location="bangalore",
    budget="high",
    cuisine="mexican",
    min_rating=3.0,
    extras=""
)
res_l2 = filter_with_fallback(df, prefs_level2)
check("Fallback Level 2 drops budget filter", 
      res_l2.fallback_level == 2 and len(res_l2.candidates) >= 3)

# Test 4: Sort Order (rating DESC, votes DESC, avg_cost_for_two ASC)
prefs_sort = UserPreferences(
    location="bangalore",
    budget="low",
    cuisine="italian",
    min_rating=4.0,
    extras=""
)
res_sort = filter_with_fallback(df, prefs_sort)
candidates = res_sort.candidates
check("Results are sorted by rating DESC", 
      candidates.iloc[0]["name"] == "A" and candidates.iloc[1]["name"] == "B",
      f"First two were {candidates.iloc[0]['name']}, {candidates.iloc[1]['name']}")

# Add edge case to test tertiary sort (avg_cost_for_two ASC)
df.loc[6] = ["G", "bangalore", "low", "italian", 4.2, 50, 300] # Same rating and votes as B, but lower cost (300 vs 400)
res_sort_edge = filter_with_fallback(df, prefs_sort)
c_edge = res_sort_edge.candidates
# A (4.5), G (4.2, 50, 300), B (4.2, 50, 400)
check("Results sorted by cost ASC when rating and votes tie",
      c_edge.iloc[1]["name"] == "G" and c_edge.iloc[2]["name"] == "B")


print(f"\n--- Results: {passed} passed, {failed} failed ---\n")
if failed:
    sys.exit(1)
