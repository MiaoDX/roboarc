status: DONE
source_plan: docs/plans/community-task-composition.md
owner: root
current_slice: all planned phases complete
last_proven: 70 Python tests pass (2 ROS skips); web unit/build/e2e pass; live community artifact validates
next_action: none
next_proof: PYTHONPATH=. .venv/bin/python scripts/validate_review_artifacts.py artifacts/tiago-proof-final
stop_condition: required live review artifact cannot be produced by product-triggered capture, or scope needs new IR/persistence/plugin seam
no_touch: core IR expansion, persistence, physical hardware, plugin loading, third robot
parked: optional second live fixture, embedded viewer exploration
