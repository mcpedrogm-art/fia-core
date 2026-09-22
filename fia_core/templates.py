"""The only project templates shipped by FIA Core."""

PROJECT = """# PROJECT

Name: <project name>
Purpose: <the problem this project solves>

## Constraints

- <constraint or leave empty>
"""

TASK = """# TASK

Status: pending

## Objective

<one concrete outcome>

## Scope

- <files, components, or boundaries included in this task>

## Done when

- <observable acceptance condition>

## Test command

python -m unittest

## Notes

<optional notes>
"""

SPEC = """# SPEC (optional)

<Only create this file when the task needs a stable technical specification.>
"""
