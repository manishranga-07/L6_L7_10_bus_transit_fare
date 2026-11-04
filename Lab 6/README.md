# L6_L7_10 — Bus Transit Fare

Lab 6: Code and Branch Coverage

## About

A small Python module that calculates bus transit fares by route type, zone traversals, and passenger concession categories, and checks contactless smartcard turnstile failure rates.

## Files

| File | Description |
|------|-------------|
| `bus_transit_fare.py` | The module under test |
| `CodeCoverageTest_bus_transit_fare.py` | Targeted test cases achieving 100% line coverage |
| `BranchCoverageTest_bus_transit_fare.py` | Targeted test cases achieving 100% branch coverage |
| `test_bus_transit.py` | Integrated test suite |
| `code_coverage_report.png` | Terminal screenshot of code coverage report |
| `branch_coverage_report.png` | Terminal screenshot of branch coverage report |

## Coverage Results

- **Line Coverage**: 100% (57/57 statements covered)
- **Branch Coverage**: 100% (40/40 branches covered)

### Commands to Run

**1. Line Coverage Analysis:**
```bash
coverage run -m pytest CodeCoverageTest_bus_transit_fare.py
coverage report -m
```

**2. Branch Coverage Analysis:**
```bash
coverage run --branch -m pytest BranchCoverageTest_bus_transit_fare.py
coverage report -m
```

Keep all your Lab 6 work in this `LAB6` folder. Lab 7 will be added to this repo later.

Refer to the lab handout for instructions.