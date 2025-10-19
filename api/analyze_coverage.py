#!/usr/bin/env python3
"""Analyze coverage.json and create a testing plan to reach 90% coverage."""

import json
from pathlib import Path

# Load coverage data
with open("coverage.json") as f:
    data = json.load(f)

files = data["files"]
totals = data["totals"]

print("=" * 80)
print("COVERAGE ANALYSIS FOR 90% TARGET")
print("=" * 80)
print(f"\nCurrent Coverage: {totals['percent_covered']:.2f}%")
print(f"Lines Covered: {totals['covered_lines']}/{totals['num_statements']}")
print(f"Missing Lines: {totals['missing_lines']}")
print(f"\nTarget: 90% coverage")
print(f"Need to cover: {int(totals['num_statements'] * 0.9 - totals['covered_lines'])} more lines")

# Categorize files by coverage
categorized = {
    "skip": [],           # 0% - probably dev scripts
    "critical": [],       # 0-40% - needs immediate attention
    "important": [],      # 40-70% - should improve
    "good": [],           # 70-90% - minor gaps
    "excellent": []       # 90%+ - well tested
}

for filepath, metrics in files.items():
    pct = metrics["summary"]["percent_covered"]
    lines = metrics["summary"]["num_statements"]
    missing = metrics["summary"]["missing_lines"]

    item = {
        "path": filepath,
        "coverage": pct,
        "lines": lines,
        "missing": missing,
        "impact": missing  # How many lines we could gain
    }

    # Skip certain files
    if any(x in filepath for x in ["clear_data.py", "seed_data.py", "__pycache__", "test_"]):
        categorized["skip"].append(item)
    elif pct >= 90:
        categorized["excellent"].append(item)
    elif pct >= 70:
        categorized["good"].append(item)
    elif pct >= 40:
        categorized["important"].append(item)
    else:
        categorized["critical"].append(item)

# Sort by impact (most missing lines first)
for category in categorized.values():
    category.sort(key=lambda x: x["impact"], reverse=True)

print("\n" + "=" * 80)
print("CRITICAL PRIORITY (0-40% coverage) - Focus Here First")
print("=" * 80)
total_critical_impact = 0
for item in categorized["critical"][:15]:  # Top 15
    print(f"{item['coverage']:5.1f}% | {item['missing']:4d} missing | {item['path']}")
    total_critical_impact += item["missing"]
print(f"\nTotal impact if all critical files reach 80%: ~{int(total_critical_impact * 0.8)} lines")

print("\n" + "=" * 80)
print("IMPORTANT (40-70% coverage) - Next Priority")
print("=" * 80)
total_important_impact = 0
for item in categorized["important"][:10]:  # Top 10
    print(f"{item['coverage']:5.1f}% | {item['missing']:4d} missing | {item['path']}")
    total_important_impact += item["missing"]

print("\n" + "=" * 80)
print("GOOD (70-90% coverage) - Fill Gaps")
print("=" * 80)
for item in categorized["good"][:10]:
    print(f"{item['coverage']:5.1f}% | {item['missing']:4d} missing | {item['path']}")

print("\n" + "=" * 80)
print("TESTING STRATEGY TO REACH 90%")
print("=" * 80)

strategies = {
    "Functions (API Endpoints)": [
        f for f in categorized["critical"] + categorized["important"]
        if "functions/" in f["path"] and f["path"].endswith(".py")
    ],
    "Repositories": [
        f for f in categorized["critical"] + categorized["important"]
        if "repositories/" in f["path"]
    ],
    "Services": [
        f for f in categorized["critical"] + categorized["important"]
        if "services/" in f["path"]
    ],
    "Shared/Core Logic": [
        f for f in categorized["critical"] + categorized["important"]
        if "shared/" in f["path"] and "repositories/" not in f["path"]
    ]
}

for category, files_list in strategies.items():
    if files_list:
        print(f"\n{category} ({len(files_list)} files):")
        impact = sum(f["missing"] for f in files_list[:5])
        for f in files_list[:5]:
            print(f"  - {Path(f['path']).name} ({f['coverage']:.1f}%, {f['missing']} lines)")
        print(f"  Top 5 impact: {impact} lines")

print("\n" + "=" * 80)
print("RECOMMENDED TEST PLAN")
print("=" * 80)
print("""
Phase 1: High-Impact API Endpoints (Target: +2000 lines, 2 weeks)
  - Create integration tests for main API endpoints
  - Focus on: forms, oauth_api, roles, permissions, organizations
  - Use real HTTP requests via func start
  - Mock only external services (Key Vault, SendGrid)

Phase 2: Repositories & Data Access (Target: +800 lines, 1 week)
  - Unit tests for repository classes
  - Mock TableStorageService at the boundary
  - Test CRUD operations, error handling, edge cases

Phase 3: Services & Utilities (Target: +600 lines, 1 week)
  - OAuth services (provider, storage)
  - File services (temp, zip, workspace)
  - Test business logic in isolation

Phase 4: Fill Coverage Gaps (Target: +400 lines, 3 days)
  - Improve existing tests to hit edge cases
  - Error handling paths
  - Validation scenarios

Estimated Total: 3800 lines covered = ~94% coverage
Time: 4-5 weeks at steady pace

CONTRACT TESTS TO CONSIDER REMOVING:
  - Most contract tests just validate Pydantic models
  - Pydantic already validates - these add little value
  - Keep only complex validation logic tests
  - Could remove ~100-150 contract tests with minimal risk
""")

print("\n" + "=" * 80)
print("FILES TO EXCLUDE FROM COVERAGE (Dev Tools)")
print("=" * 80)
dev_files = [f for f in categorized["skip"] if not "test_" in f["path"]]
for f in dev_files:
    print(f"  - {f['path']}")
print("\nAdd these to .coveragerc [run] omit section")
