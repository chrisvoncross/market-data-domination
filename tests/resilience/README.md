# Resilience Test Matrix

This directory contains resilience-focused tests only.
It does not modify production runtime code paths.

## Test files

- `test_fault_injection_matrix.py`
  - connect-failure retry/backoff behavior
  - reconnect-cycle behavior
  - queue-drop injection behavior
- `test_report_gate_matrix.py`
  - pass/fail gate semantics for resilience reports
  - required channel coverage enforcement
  - parse/connect failure gate enforcement
- `test_resilience_report.py`
  - validates generated resilience report status when present

## Gate intent

The resilience gate is considered passing only when:

- run status is `ok`
- no parse errors
- no connect failures
- no missing required channels
- required channel counters are populated

## How to run

- Unit/fault matrix only:
  - `PYTHONPATH=src .venv/bin/python -m unittest tests/resilience/test_fault_injection_matrix.py tests/resilience/test_report_gate_matrix.py tests/resilience/test_resilience_report.py`
- Full live resilience validation:
  - `scripts/validate_resilience.sh 60 120`
