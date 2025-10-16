#!/usr/bin/env python3
"""
Fix Azure Functions Blueprint function_name parameter
Convert from invalid syntax:
  @bp.route(route="...", methods=["..."], function_name="...")
To valid syntax:
  @bp.function_name("...")
  @bp.route(route="...", methods=["..."])
"""
import re


def fix_function_names(filepath):
    with open(filepath) as f:
        content = f.read()

    # Pattern to match: @bp.route(route="...", methods=[...], function_name="name")
    pattern = r'@bp\.route\(route="([^"]+)",\s*methods=(\[[^\]]+\])(?:,\s*function_name="([^"]+)")?\)'

    def replacer(match):
        route = match.group(1)
        methods = match.group(2)
        func_name = match.group(3)

        if func_name:
            # If function_name was present, move it to separate decorator
            return f'@bp.function_name("{func_name}")\n@bp.route(route="{route}", methods={methods})'
        else:
            # No function_name, keep as-is
            return match.group(0)

    fixed_content = re.sub(pattern, replacer, content)

    with open(filepath, 'w') as f:
        f.write(fixed_content)

    print(f"Fixed {filepath}")

if __name__ == "__main__":
    files = [
        "functions/roles.py",
        "functions/organizations.py",
        "functions/permissions.py",
        "functions/org_config.py"
    ]

    for filepath in files:
        fix_function_names(filepath)
