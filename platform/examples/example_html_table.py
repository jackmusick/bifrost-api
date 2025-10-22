"""
HTML Table Example Workflow

Demonstrates returning formatted HTML output from a workflow.
The platform automatically detects HTML responses (strings starting with '<')
and renders them appropriately in the UI.
"""

from bifrost import OrganizationContext, param, workflow


@workflow(
    name="html_table_example",
    description="Generate a pretty HTML table with sample data",
    category="examples",
    tags=["example", "html", "reporting"],
    execution_mode="sync"
)
@param("title", type="string", label="Table Title", required=False, default_value="Sample Data Report", help_text="Title for the HTML table")
@param("row_count", type="int", label="Number of Rows", required=False, default_value=5, help_text="Number of data rows to generate (1-50)")
@param("theme", type="string", label="Color Theme", required=False, default_value="blue", help_text="Color theme: blue, green, purple, or orange")
async def html_table_example(
    context: OrganizationContext,
    title: str = "Sample Data Report",
    row_count: int = 5,
    theme: str = "blue"
) -> str:
    """
    Generate a pretty HTML table with sample data.

    This workflow demonstrates how to return HTML from a workflow.
    The platform automatically detects HTML responses and renders them
    in the UI with proper formatting.

    Args:
        context: Organization context
        title: Title for the table
        row_count: Number of rows to generate (1-50)
        theme: Color theme (blue, green, purple, orange)

    Returns:
        HTML string with formatted table
    """
    import datetime
    import random

    # Validate inputs
    row_count = max(1, min(50, row_count))  # Clamp between 1-50

    # Theme colors
    themes = {
        "blue": {"primary": "#3b82f6", "secondary": "#dbeafe", "hover": "#bfdbfe"},
        "green": {"primary": "#10b981", "secondary": "#d1fae5", "hover": "#a7f3d0"},
        "purple": {"primary": "#8b5cf6", "secondary": "#ede9fe", "hover": "#ddd6fe"},
        "orange": {"primary": "#f59e0b", "secondary": "#fed7aa", "hover": "#fcd34d"}
    }
    colors = themes.get(theme.lower(), themes["blue"])

    context.info(f"Generating HTML table with {row_count} rows using {theme} theme")

    # Sample data generator
    products = ["Widget", "Gadget", "Doohickey", "Thingamajig", "Whatchamacallit"]
    statuses = ["Active", "Pending", "Completed", "On Hold"]

    # Build table rows
    rows_html = ""
    total_amount = 0.0

    for i in range(row_count):
        product = random.choice(products)
        status = random.choice(statuses)
        quantity = random.randint(1, 100)
        price = round(random.uniform(10.0, 500.0), 2)
        amount = round(quantity * price, 2)
        total_amount += amount

        # Status badge color
        status_colors = {
            "Active": "#10b981",
            "Pending": "#f59e0b",
            "Completed": "#3b82f6",
            "On Hold": "#6b7280"
        }
        status_color = status_colors.get(status, "#6b7280")

        rows_html += f"""
        <tr>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb;">{i + 1}</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; font-weight: 500;">{product}</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center;">
                <span style="
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 9999px;
                    font-size: 12px;
                    font-weight: 600;
                    background-color: {status_color}20;
                    color: {status_color};
                ">{status}</span>
            </td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: right;">{quantity}</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: right;">${price:,.2f}</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600;">${amount:,.2f}</td>
        </tr>"""

    # Generate timestamp
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build complete HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, {colors['secondary']} 0%, #ffffff 100%);
            padding: 40px 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 24px;
        }}
        h1 {{
            color: {colors['primary']};
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .subtitle {{
            color: #6b7280;
            font-size: 14px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead {{
            background: {colors['primary']};
            color: white;
        }}
        thead th {{
            padding: 16px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        thead th:nth-child(4),
        thead th:nth-child(5),
        thead th:nth-child(6) {{
            text-align: right;
        }}
        tbody tr:hover {{
            background-color: {colors['hover']};
        }}
        tfoot {{
            background: #f9fafb;
            font-weight: 600;
        }}
        tfoot td {{
            padding: 16px;
            border-top: 2px solid {colors['primary']};
        }}
        .footer {{
            margin-top: 24px;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            background: {colors['secondary']};
            color: {colors['primary']};
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p class="subtitle">Generated on {timestamp} • Organization: {context.org_id or 'Global'}</p>
        </div>

        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Product</th>
                        <th style="text-align: center;">Status</th>
                        <th style="text-align: right;">Quantity</th>
                        <th style="text-align: right;">Unit Price</th>
                        <th style="text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="5" style="text-align: right;">Total:</td>
                        <td style="text-align: right; color: {colors['primary']}; font-size: 18px;">${total_amount:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Bifrost Workflows • Powered by {context.caller.name}</p>
        </div>
    </div>
</body>
</html>"""

    context.save_checkpoint("table_generated", {
        "row_count": row_count,
        "total_amount": total_amount,
        "theme": theme
    })

    context.info(f"HTML table generated successfully with total amount: ${total_amount:,.2f}")

    return html
