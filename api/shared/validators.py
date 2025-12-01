"""
Form Validation Logic
Circular dependency detection and field reference validation
Created for T013-T016
"""

import re

from shared.models import FormField, DataProviderInputMode


def extract_field_references(expression: str) -> set[str]:
    """
    Extract field references from a JavaScript expression (T015).

    Matches patterns like:
    - context.field.field_name
    - context.field["field_name"]
    - context.field['field_name']

    Args:
        expression: JavaScript expression string

    Returns:
        Set of field names referenced in the expression

    Examples:
        >>> extract_field_references("context.field.first_name + context.field.last_name")
        {'first_name', 'last_name'}
        >>> extract_field_references("context.field['token']")
        {'token'}
    """
    field_refs = set()

    # Match context.field.field_name (dot notation)
    dot_pattern = r'context\.field\.([a-zA-Z_][a-zA-Z0-9_]*)'
    dot_matches = re.findall(dot_pattern, expression)
    field_refs.update(dot_matches)

    # Match context.field["field_name"] or context.field['field_name'] (bracket notation)
    bracket_pattern = r'context\.field\[["\']([^"\']+)["\']\]'
    bracket_matches = re.findall(bracket_pattern, expression)
    field_refs.update(bracket_matches)

    return field_refs


def build_dependency_graph(fields: list[FormField]) -> dict[str, set[str]]:
    """
    Build dependency graph from form fields (T016).

    Creates an adjacency list showing which fields each field depends on
    based on dataProviderInputs configurations.

    Args:
        fields: List of form fields

    Returns:
        Dictionary mapping field_name -> set of dependent field names

    Example:
        field_a depends on field_b and field_c
        field_b depends on nothing
        field_c depends on nothing

        Returns: {
            "field_a": {"field_b", "field_c"},
            "field_b": set(),
            "field_c": set()
        }
    """
    graph: dict[str, set[str]] = {}

    # Initialize graph with all fields
    for field in fields:
        graph[field.name] = set()

    # Build dependencies from dataProviderInputs
    for field in fields:
        if not field.dataProviderInputs:
            continue

        dependencies = set()

        for param_name, input_config in field.dataProviderInputs.items():
            if input_config.mode == DataProviderInputMode.FIELD_REF:
                # Direct field reference
                if input_config.fieldName:
                    dependencies.add(input_config.fieldName)

            elif input_config.mode == DataProviderInputMode.EXPRESSION:
                # Extract field references from expression
                if input_config.expression:
                    expr_refs = extract_field_references(input_config.expression)
                    dependencies.update(expr_refs)

        graph[field.name] = dependencies

    return graph


def detect_circular_dependencies(fields: list[FormField]) -> list[str]:
    """
    Detect circular dependencies in form field configuration (T014).

    Uses depth-first search to find cycles in the dependency graph.

    Args:
        fields: List of form fields

    Returns:
        List of error messages for each cycle found.
        Empty list if no cycles detected.

    Example error message:
        "Circular dependency detected: field_a → field_b → field_c → field_a"
    """
    graph = build_dependency_graph(fields)
    errors = []

    # Track visited nodes and current path
    visited = set()
    rec_stack = set()
    current_path = []

    def dfs(node: str) -> bool:
        """
        Depth-first search to detect cycles.

        Returns:
            True if cycle detected, False otherwise
        """
        visited.add(node)
        rec_stack.add(node)
        current_path.append(node)

        # Visit all dependencies
        for neighbor in graph.get(node, set()):
            if neighbor not in graph:
                # Referenced field doesn't exist (will be caught by other validation)
                continue

            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Cycle detected!
                cycle_start_idx = current_path.index(neighbor)
                cycle = current_path[cycle_start_idx:] + [neighbor]
                cycle_str = " → ".join(cycle)
                errors.append(f"Circular dependency detected: {cycle_str}")
                return True

        # Backtrack
        current_path.pop()
        rec_stack.remove(node)
        return False

    # Check all nodes (handles disconnected graphs)
    for field in fields:
        if field.name not in visited:
            dfs(field.name)

    return errors


def validate_field_references(fields: list[FormField]) -> list[str]:
    """
    Validate that field references exist and appear earlier in the form.

    Args:
        fields: List of form fields

    Returns:
        List of validation error messages

    Checks:
        1. Referenced fields exist in the form
        2. Referenced fields appear earlier in the field order (prevents forward refs)
    """
    errors = []
    field_names = {field.name for field in fields}
    field_positions = {field.name: idx for idx, field in enumerate(fields)}

    for field in fields:
        if not field.dataProviderInputs:
            continue

        field_pos = field_positions[field.name]

        for param_name, input_config in field.dataProviderInputs.items():
            referenced_fields = set()

            if input_config.mode == DataProviderInputMode.FIELD_REF:
                if input_config.fieldName:
                    referenced_fields.add(input_config.fieldName)

            elif input_config.mode == DataProviderInputMode.EXPRESSION:
                if input_config.expression:
                    referenced_fields = extract_field_references(input_config.expression)

            for ref_field in referenced_fields:
                # Check if field exists
                if ref_field not in field_names:
                    errors.append(
                        f"Field '{field.name}' references non-existent field '{ref_field}' "
                        f"in data provider input '{param_name}'"
                    )
                    continue

                # Check if field appears earlier
                ref_pos = field_positions.get(ref_field)
                if ref_pos is not None and ref_pos >= field_pos:
                    errors.append(
                        f"Field '{field.name}' references field '{ref_field}' which appears "
                        f"later in the form (forward reference not allowed)"
                    )

    return errors
