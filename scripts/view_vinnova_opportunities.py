import sys
import os
import webbrowser
from datetime import datetime
import json
import html

# Add project root to path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.connectors.vinnova_rounds import fetch
from app.normalize import normalize_vinnova

# HTML Template with DataTables and Buttons (ColVis)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vinnova Funding Opportunities</title>
    
    <!-- DataTables CSS -->
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
    
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f6f9; color: #333; }
        .container { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { margin-top: 0; color: #2c3e50; }
        .meta { color: #7f8c8d; margin-bottom: 20px; font-size: 0.9em; }
        
        /* Status Badges */
        .status-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; text-transform: uppercase; }
        .status-open { background-color: #d4edda; color: #155724; }
        .status-closed { background-color: #f8d7da; color: #721c24; }
        .status-forthcoming { background-color: #fff3cd; color: #856404; }
        
        a.btn-link { color: #007bff; text-decoration: none; font-weight: 500; }
        a.btn-link:hover { text-decoration: underline; }
        
        /* Table Tweaks */
        table.dataTable thead th { background-color: #f8f9fa; }
        td { vertical-align: top; }
        pre { white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em; background: #f8f9fa; padding: 5px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Vinnova Funding Opportunities</h1>
        <div class="meta">
            Generated on <strong>__DATE__</strong> | Total Items: <strong>__COUNT__</strong>
        </div>
        
        <table id="grantsTable" class="display" style="width:100%">
            <thead>
                <tr>
                    __THEAD_ROWS__
                </tr>
            </thead>
            <tbody>
                __TBODY_ROWS__
            </tbody>
        </table>
    </div>

    <!-- jQuery & DataTables JS -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.colVis.min.js"></script>
    
    __SCRIPT__
</body>
</html>
"""

def main():
    print("--- Generating Vinnova Opportunities Report ---")
    
    items = []
    print("Fetching data from Vinnova API...")
    try:
        for i, raw in enumerate(fetch()):
            try:
                norm = normalize_vinnova(raw)
                items.append(norm)
            except Exception as e:
                print(f"Error normalizing item {i}: {e}")
            print(f"Fetched {len(items)} items...", end="\r")
    except Exception as e:
        print(f"\nError fetching data: {e}")
    
    print(f"\nProcessing {len(items)} items into HTML...")

    if not items:
        print("No items found. Exiting.")
        return

    # --- DYNAMIC COLUMN AND ROW GENERATION ---

    # 1. Define primary columns to show by default and find all unique columns
    primary_cols = ['id', 'status', 'title', 'deadline_date', 'programme', 'source']
    all_cols = set()
    for item in items:
        all_cols.update(item.keys())
    
    # Create the final header order: primary first, then the rest sorted
    other_cols = sorted(list(all_cols - set(primary_cols)))
    header_cols = primary_cols + other_cols
    # Add a special 'View Link' column at the end for user convenience
    header_cols.append('view_link')

    # 2. Generate table headers
    thead_html = ""
    for col in header_cols:
        display_name = col.replace('_', ' ').title()
        thead_html += f"<th>{html.escape(display_name)}</th>"

    # 3. Generate table rows
    tbody_html = ""
    for item in items:
        tbody_html += "<tr>"
        for col_key in header_cols:
            value = item.get(col_key)
            
            # Special formatting for specific columns
            if col_key == 'status':
                status_lower = str(value).lower()
                status_class = ""
                if "open" in status_lower: status_class = "status-open"
                elif "closed" in status_lower: status_class = "status-closed"
                elif "forthcoming" in status_lower or "upcoming" in status_lower: status_class = "status-forthcoming"
                cell_content = f'<span class="status-badge {status_class}">{html.escape(str(value))}</span>'
            
            elif col_key == 'title':
                # Prefer Swedish for Vinnova, fallback to English
                if isinstance(value, dict):
                    title_text = value.get('sv') or value.get('en') or 'No Title'
                else:
                    title_text = str(value) if value is not None else 'No Title'
                cell_content = html.escape(title_text)

            elif col_key == 'view_link':
                url = item.get("links", {}).get("landing") or "#"
                cell_content = f'<a href="{url}" class="btn-link" target="_blank">View Call</a>'

            elif isinstance(value, (dict, list)):
                pretty_json = json.dumps(value, indent=2, ensure_ascii=False)
                cell_content = f"<pre><code>{html.escape(pretty_json)}</code></pre>"
            
            else:
                cell_content = html.escape(str(value) if value is not None else "")
            
            tbody_html += f"<td>{cell_content}</td>"
        
        tbody_html += "</tr>"

    # 4. Configure DataTables JS
    hidden_indices = [i for i, col in enumerate(header_cols) if col not in primary_cols and col != 'view_link']
    try:
        deadline_idx = header_cols.index('deadline_date')
    except ValueError:
        deadline_idx = 0

    script_html = f"""
    <script>
        $(document).ready(function() {{
            $('#grantsTable').DataTable({{
                dom: 'Bfrtip', buttons: [{{ extend: 'colvis', text: 'Select Columns' }}, 'pageLength'],
                pageLength: 25, order: [[{deadline_idx}, 'asc']],
                columnDefs: [ {{ targets: {hidden_indices}, visible: false }} ]
            }});
        }});
    </script>
    """
    # Fill template
    html_content = HTML_TEMPLATE.replace("__COUNT__", str(len(items)))
    html_content = html_content.replace("__DATE__", datetime.now().strftime("%Y-%m-%d %H:%M"))
    html_content = html_content.replace("__THEAD_ROWS__", thead_html)
    html_content = html_content.replace("__TBODY_ROWS__", tbody_html)
    html_content = html_content.replace("__SCRIPT__", script_html)

    # Save to file
    output_file = os.path.abspath("vinnova_opportunities.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated: {output_file}")
    
    # Attempt to open in default browser
    try:
        webbrowser.open('file://' + output_file)
    except Exception:
        print("Could not open browser automatically. Please open the file manually.")

if __name__ == "__main__":
    main()