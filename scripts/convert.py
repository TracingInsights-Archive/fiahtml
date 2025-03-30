import os
import json
import requests
import subprocess
import shutil
from datetime import datetime
import time

# Configuration
OUTPUT_DIR = "docs"  # Changed from "output/html" to "docs" for GitHub Pages
GROBID_URL = "http://localhost:8070"  # GROBID service URL when running locally

def ensure_dir(directory):
    """Ensure the directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def convert_pdf_to_html_with_grobid(pdf_path, output_dir):
    """Convert a PDF to HTML using GROBID"""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    html_dir = os.path.join(output_dir, f"{pdf_name}_{timestamp}")
    ensure_dir(html_dir)

    html_file = os.path.join(html_dir, f"{pdf_name}.html")

    try:
        # Call GROBID API to process the PDF
        with open(pdf_path, 'rb') as pdf:
            # First, process the full text
            response = requests.post(
                f"{GROBID_URL}/api/processFulltextDocument",
                files={'input': pdf},
                data={'consolidateHeader': '1', 'includeRawCitations': '1'}
            )

            if response.status_code != 200:
                raise Exception(f"GROBID API returned status code {response.status_code}")

            # Save the TEI XML response
            tei_file = os.path.join(html_dir, f"{pdf_name}.tei.xml")
            with open(tei_file, 'w', encoding='utf-8') as f:
                f.write(response.text)

            # Convert TEI to HTML
            html_content = tei_to_html(response.text, pdf_name)

            # Save the HTML
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            return {
                "html_path": html_file,
                "html_dir": html_dir,
                "success": True
            }
    except Exception as e:
        print(f"Error converting {pdf_path}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def tei_to_html(tei_content, title):
    """Convert TEI XML to HTML"""
    # This is a simplified conversion - in a real implementation,
    # you would use a proper XML parser and create a more sophisticated HTML output

    # Basic HTML template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .abstract {{ background-color: #f9f9f9; padding: 15px; border-left: 4px solid #ddd; margin-bottom: 20px; }}
        .section {{ margin-bottom: 20px; }}
        .figure {{ text-align: center; margin: 20px 0; }}
        .figure img {{ max-width: 100%; }}
        .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .table th, .table td {{ border: 1px solid #ddd; padding: 8px; }}
        .table th {{ background-color: #f2f2f2; }}
        .reference {{ margin-bottom: 10px; padding-left: 20px; text-indent: -20px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">
{content}
    </div>
</body>
</html>
"""

    # Extract content from TEI
    # This is a very simplified extraction - a real implementation would be more thorough
    import re
    from html import escape

    # Extract title if not provided
    if not title:
        title_match = re.search(r'<title[^>]*>(.*?)</title>', tei_content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "Converted Document"

    # Extract abstract
    abstract = ""
    abstract_match = re.search(r'<abstract>(.*?)</abstract>', tei_content, re.DOTALL)
    if abstract_match:
        abstract = f'<div class="abstract"><h2>Abstract</h2>{abstract_match.group(1)}</div>'

    # Extract body text
    body_content = ""
    body_match = re.search(r'<body>(.*?)</body>', tei_content, re.DOTALL)
    if body_match:
        body_text = body_match.group(1)

        # Convert sections
        body_text = re.sub(r'<div[^>]*type="section"[^>]*>', '<div class="section">', body_text)

        # Convert headings
        body_text = re.sub(r'<head>(.*?)</head>', r'<h2>\1</h2>', body_text)

        # Convert paragraphs
        body_text = re.sub(r'<p>(.*?)</p>', r'<p>\1</p>', body_text)

        body_content = body_text

    # Combine content
    content = abstract + body_content

    # Clean up XML tags that we don't want in HTML
    content = re.sub(r'<[/]?(tei|text|TEI|div)[^>]*>', '', content)

    # Fill template
    html_content = html_template.format(
        title=escape(title),
        content=content
    )

    return html_content

def start_grobid_docker():
    """Start GROBID Docker container if not already running"""
    try:
        # Check if GROBID container is already running
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "name=grobid"],
            capture_output=True, text=True, check=True
        )

        if not result.stdout.strip():
            print("Starting GROBID Docker container...")
            subprocess.run(
                ["docker", "run", "--rm", "-d", "--name", "grobid", "-p", "8070:8070", "lfoppiano/grobid:0.7.2"],
                check=True
            )

            # Wait for GROBID to start
            print("Waiting for GROBID to start...")
            max_retries = 10
            for i in range(max_retries):
                try:
                    response = requests.get(f"{GROBID_URL}/api/isalive")
                    if response.status_code == 200:
                        print("GROBID is ready!")
                        break
                except:
                    pass

                print(f"Waiting for GROBID to start (attempt {i+1}/{max_retries})...")
                time.sleep(5)
        else:
            print("GROBID Docker container is already running")
    except Exception as e:
        print(f"Error starting GROBID Docker container: {str(e)}")
        print("Please make sure Docker is installed and running")

def convert_pdfs():
    """Convert all downloaded PDFs to HTML"""
    ensure_dir(OUTPUT_DIR)

    if not os.path.exists("downloaded_pdfs.json"):
        print("No PDFs to convert")
        return []

    # Start GROBID Docker container
    start_grobid_docker()

    with open("downloaded_pdfs.json", "r") as f:
        downloaded_pdfs = json.load(f)

    converted_pdfs = []
    for pdf_info in downloaded_pdfs:
        if "local_path" in pdf_info and os.path.exists(pdf_info["local_path"]):
            print(f"Converting {pdf_info['local_path']} to HTML")
            result = convert_pdf_to_html_with_grobid(pdf_info["local_path"], OUTPUT_DIR)

            # Merge the conversion result with the original PDF info
            converted_pdf = {**pdf_info, **result}
            converted_pdfs.append(converted_pdf)
        else:
            print(f"PDF file not found: {pdf_info.get('local_path', 'unknown')}")

    # Create an index page
    if converted_pdfs:
        create_index_page(converted_pdfs, OUTPUT_DIR)

    # Save the conversion results
    with open("converted_pdfs.json", "w") as f:
        json.dump(converted_pdfs, f, indent=2)

    # Create a root index.html file for GitHub Pages
    create_root_index(OUTPUT_DIR)
    
    # Create a .nojekyll file to disable Jekyll processing on GitHub Pages
    nojekyll_path = os.path.join(OUTPUT_DIR, ".nojekyll")
    with open(nojekyll_path, "w") as f:
        pass  # Create an empty file
    print(f"Created .nojekyll file at {nojekyll_path}")

    return converted_pdfs


def create_index_page(converted_pdfs, output_dir):
    """Create an index.html page that lists all converted PDFs"""
    index_path = os.path.join(output_dir, "index.html")

    # Simple HTML template for the index page
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIA Documents</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ margin-bottom: 10px; padding: 10px; border-bottom: 1px solid #eee; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .date {{ color: #666; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>FIA Documents</h1>
    <p>Last updated: {date}</p>
    <ul>
{items}
    </ul>
</body>
</html>
"""

    # Generate list items for each converted PDF
    items = []
    for pdf in converted_pdfs:
        if pdf.get("success", False):
            relative_path = os.path.relpath(pdf["html_path"], output_dir)
            title = pdf.get("title", os.path.basename(relative_path))
            date = pdf.get("date", "Unknown date")
            items.append(f'        <li><a href="{relative_path}">{title}</a> <span class="date">{date}</span></li>')

    # Fill in the template
    html_content = html_content.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        items="\n".join(items)
    )

    # Write the index page
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return index_path

def create_root_index(output_dir):
    """Create an improved index.html file in the root directory for GitHub Pages"""
    # Find all HTML files in the output directory
    html_files = []
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

    # HTML template with improved styling - properly escaped curly braces for CSS
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FIA Documents Archive</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        header {{
            background-color: #e10600;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .last-updated {{
            margin-top: 10px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        .document-list {{
            list-style-type: none;
            padding: 0;
        }}
        .document-item {{
            background-color: white;
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .document-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .document-link {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
            font-size: 1.1em;
            display: block;
            margin-bottom: 5px;
        }}
        .document-link:hover {{
            text-decoration: underline;
        }}
        .document-date {{
            color: #666;
            font-size: 0.9em;
        }}
        .no-documents {{
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            color: #666;
        }}
        footer {{
            margin-top: 30px;
            text-align: center;
            font-size: 0.9em;
            color: #666;
        }}
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
    html_content = html_template.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        content=content
    )

    # Write the index page to the root directory
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Created improved index page at {index_path}")
    return index_path

if __name__ == "__main__":
    converted = convert_pdfs()
    print(f"Converted {len(converted)} PDFs to HTML")
