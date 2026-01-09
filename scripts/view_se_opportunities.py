import sys
import os
import webbrowser
from datetime import datetime
import json
import html
from dotenv import load_dotenv

# Add project root to path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.connectors.formas import FormasConnector
from app.connectors.forte import ForteConnector
from app.connectors.vr import VrConnector
from app.normalize import normalize_se_generic

# HTML Template with DataTables and Buttons (ColVis)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Swedish Research Funding Opportunities</title>
    
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
        <h1>Swedish Research Funding (Formas, Forte, VR)</h1>
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
    print("--- Generating SE Generic Opportunities Report ---")
    load_dotenv()

    connectors = [
        FormasConnector(),
        ForteConnector(),
        VrConnector()
    ]
    
    items = []
    
    for connector in connectors:
        print(f"Fetching data from {connector.name}...")
        try:
            raw_items = connector.fetch()
            print(f"  Found {len(raw_items)} items.")
            for i, raw in enumerate(raw_items):
                try:
                    norm = normalize_se_generic(raw)
                    items.append(norm)
                except Exception as e:
                    print(f"  Error normalizing item {i} from {connector.name}: {e}")
        except Exception as e:
            print(f"  Error fetching data from {connector.name}: {e}")
    
    print(f"\nProcessing {len(items)} total items into HTML...")

    if not items:
        print("No items found. Exiting.")
        return

    # 1. Define columns
    primary_cols = ['source', 'status', 'title', 'deadline_date', 'call_identifier']
    all_cols = set()
    for item in items:
        all_cols.update(item.keys())
    
    other_cols = sorted(list(all_cols - set(primary_cols)))
    header_cols = primary_cols + other_cols
    header_cols.append('view_link')

    # 2. Generate headers
    thead_html = "".join([f"<th>{html.escape(c.replace('_', ' ').title())}</th>" for c in header_cols])

    # 3. Generate rows
    tbody_html = ""
    for item in items:
        tbody_html += "<tr>"
        for col_key in header_cols:
            value = item.get(col_key)
            
            if col_key == 'status':
                status_lower = str(value).lower()
                status_class = "status-forthcoming" if "forthcoming" in status_lower else \
                               "status-open" if "open" in status_lower else \
                               "status-closed" if "closed" in status_lower else ""
                cell_content = f'<span class="status-badge {status_class}">{html.escape(str(value))}</span>'
            elif col_key == 'title':
                title_text = (value.get('en') or value.get('sv') or 'No Title') if isinstance(value, dict) else str(value)
                cell_content = html.escape(title_text)
            elif col_key == 'view_link':
                url = item.get("links", {}).get("landing") or "#"
                cell_content = f'<a href="{url}" class="btn-link" target="_blank">View</a>'
            elif isinstance(value, (dict, list)):
                cell_content = f"<pre><code>{html.escape(json.dumps(value, indent=2, ensure_ascii=False))}</code></pre>"
            else:
                cell_content = html.escape(str(value) if value is not None else "")
            
            tbody_html += f"<td>{cell_content}</td>"
        tbody_html += "</tr>"

    # 4. Fill template
    hidden_targets = [i for i, c in enumerate(header_cols) if c not in primary_cols and c != 'view_link']

    script_html = f"""
    <script>
    $(document).ready(function() {{
        // Clone the header row to create filters
        $('#grantsTable thead tr').clone(true).addClass('filters').appendTo('#grantsTable thead');

        var table = $('#grantsTable').DataTable({{
            dom: 'Bfrtip',
            buttons: ['colvis', 'pageLength'],
            pageLength: 25,
            order: [[3, 'asc']],
            orderCellsTop: true,
            columnDefs: [ 
                {{ targets: {hidden_targets}, visible: false }} 
            ],
            initComplete: function () {{
                var api = this.api();

                // For each column
                api.columns().eq(0).each(function (colIdx) {{
                    // Set the header cell to contain the input element
                    var cell = $('.filters th').eq(
                        $(api.column(colIdx).header()).index()
                    );
                    var title = $(cell).text();
                    $(cell).html('<input type="text" placeholder="Filter" style="width: 100%; font-size: 0.9em; padding: 2px; box-sizing: border-box;" />');

                    // On every keypress in this input
                    $('input', cell)
                        .off('keyup change')
                        .on('keyup change', function (e) {{
                            e.stopPropagation();
                            
                            // Get the search value
                            $(this).attr('title', $(this).val());
                            var regexr = '({{search}})'; 
                            
                            var cursorPosition = this.selectionStart;
                            // Search the column for that value
                            api.column(colIdx).search(this.value).draw();
                        }});
                }});
            }}
        }});
    }});
    </script>
    """

    html_content = HTML_TEMPLATE.replace("__COUNT__", str(len(items))).replace("__DATE__", datetime.now().strftime("%Y-%m-%d %H:%M")).replace("__THEAD_ROWS__", thead_html).replace("__TBODY_ROWS__", tbody_html).replace("__SCRIPT__", script_html)

    output_file = os.path.abspath("se_opportunities.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated: {output_file}")
    webbrowser.open('file://' + output_file)

if __name__ == "__main__":
    main()