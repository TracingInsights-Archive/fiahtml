import os
import json
import glob
from datetime import datetime

def find_html_files(output_dir):
    """Find all HTML files in the output directory and its subdirectories"""
    html_files = []

    # Find all HTML files in the output directory and its subdirectories
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.html') and file != 'index.html':
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, output_dir)

                # Try to extract a title from the HTML file
                title = os.path.splitext(os.path.basename(file))[0]
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        title_match = content.split('<title>')[1].split('</title>')[0] if '<title>' in content else title
                        title = title_match.strip()
                except Exception:
                    pass  # Use the filename as title if extraction fails

                # Get the file's modification time as the date
                mod_time = os.path.getmtime(full_path)
                date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d')

                html_files.append({
                    'path': relative_path,
                    'title': title,
                    'date': date
                })

    # Sort by date (newest first)
    html_files.sort(key=lambda x: x['date'], reverse=True)
    return html_files

def create_root_index(output_dir):
    """Create an index.html file in the root directory"""
    html_files = find_html_files(output_dir)

    # HTML template with improved styling
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIA Documents Archive</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        header {
            background-color: #e10600;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            margin: 0;
            font-size: 2em;
        }
        .last-updated {
            margin-top: 10px;
            font-size: 0.9em;
            opacity: 0.8;
        }
        .document-list {
            list-style-type: none;
            padding: 0;
        }
        .document-item {
            background-color: white;
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .document-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .document-link {
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
            font-size: 1.1em;
            display: block;
            margin-bottom: 5px;
        }
        .document-link:hover {
            text-decoration: underline;
        }
        .document-date {
            color: #666;
            font-size: 0.9em;
        }
        .no-documents {
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            color: #666;
        }
        footer {
            margin-top: 30px;
            text-align: center;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <header>
        <h1>FIA Documents Archive</h1>
        <div class="last-updated">Last updated: {date}</div>
    </header>

    {content}

    <footer>
        <p>This archive is automatically updated with the latest documents from the FIA website.</p>
    </footer>
</body>
</html>
"""


    if html_files:
        # Generate list items for each HTML file
        items = []
        for file in html_files:
            items.append(f'        <li class="document-item">\n            <a href="{file["path"]}" class="document-link">{file["title"]}</a>\n            <span class="document-date">{file["date"]}</span>\n        </li>')

        content = f'    <ul class="document-list">\n{"".join(items)}\n    </ul>'
    else:
        content = '    <div class="no-documents">No documents available yet.</div>'

    # Fill in the template
    html_content = html_content.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        content=content
    )

    # Write the index page to the root directory
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return index_path

if __name__ == "__main__":
    # Default output directory is 'docs' for GitHub Pages
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    index_path = create_root_index(output_dir)
    print(f"Created index page at {index_path}")
