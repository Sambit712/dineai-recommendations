"""Phase 3 unit tests -- run with: python tests/test_input_handler.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input.handler import (
    _sanitize,
    _sanitize_extras,
    _is_ascii,
    VALID_BUDGETS,
    MIN_CUISINE_LEN,
    MAX_EXTRAS_LEN,
    RATING_MIN,
    RATING_MAX,
)
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

print("\n--- Phase 3: Input Handler Unit Tests ---\n")

# EC-I06 -- special character sanitization
check("Sanitize 'Delhi!@#' -> 'Delhi'",
      _sanitize("Delhi!@#") == "Delhi",
      f"got: '{_sanitize('Delhi!@#')}'")

check("Sanitize '<script>xss</script>' strips angle brackets",
      "<" not in _sanitize("<script>xss</script>"),
      f"got: '{_sanitize('<script>xss</script>')}'")

check("Sanitize 'North-Delhi' keeps hyphen",
      _sanitize("North-Delhi") == "North-Delhi",
      f"got: '{_sanitize('North-Delhi')}'")

check("Sanitize empty string -> empty",
      _sanitize("   ") == "",
      f"got: '{_sanitize('   ')}'")

# EC-I07 -- extras sanitization and length
long_extras = "A" * 500
check("Extras sanitize allows comma and hyphen",
      _sanitize_extras("family-friendly, quick service.") == "family-friendly, quick service.",
      f"got: '{_sanitize_extras('family-friendly, quick service.')}'")

check(f"MAX_EXTRAS_LEN is {MAX_EXTRAS_LEN}",
      len(_sanitize_extras(long_extras)) == 500,   # sanitize doesn't truncate, main flow does
      f"sanitize alone returned len {len(_sanitize_extras(long_extras))}")

# EC-I08 -- ASCII detection
check("ASCII check: 'Bangalore' -> True",
      _is_ascii("Bangalore") is True)

check("ASCII check: 'delhi' -> True",
      _is_ascii("delhi") is True)

# EC-I03 -- budget validation set
check("'low' in VALID_BUDGETS",     "low"    in VALID_BUDGETS)
check("'medium' in VALID_BUDGETS",  "medium" in VALID_BUDGETS)
check("'high' in VALID_BUDGETS",    "high"   in VALID_BUDGETS)
check("'extreme' not in VALID_BUDGETS", "extreme" not in VALID_BUDGETS)
check("'MEDIUM' not in VALID_BUDGETS (raw)", "MEDIUM" not in VALID_BUDGETS)  # handler lowercases

# EC-I04 -- rating bounds
check("RATING_MIN is 0.0", RATING_MIN == 0.0)
check("RATING_MAX is 5.0", RATING_MAX == 5.0)

# EC-F03 guard
check(f"MIN_CUISINE_LEN >= 2", MIN_CUISINE_LEN >= 2)

# UserPreferences dataclass
prefs = UserPreferences(
    location="bangalore",
    budget="medium",
    cuisine="north indian",
    min_rating=4.0,
    extras="family-friendly",
)
check("UserPreferences.location", prefs.location == "bangalore")
check("UserPreferences.budget",   prefs.budget == "medium")
check("UserPreferences.cuisine",  prefs.cuisine == "north indian")
check("UserPreferences.min_rating", prefs.min_rating == 4.0)
check("UserPreferences.extras",   prefs.extras == "family-friendly")

print(f"\n--- Results: {passed} passed, {failed} failed ---\n")
if failed:
    sys.exit(1)
