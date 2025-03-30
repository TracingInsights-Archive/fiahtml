import os
import json
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import re
import subprocess
import shutil
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
FIA_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/"
PROCESSED_FILE = "processed_pdfs.json"
OUTPUT_DIR = "docs"
HTML_DIR = os.path.join(OUTPUT_DIR, "html")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdf")

def ensure_directories():
    """Ensure all necessary directories exist."""
    for directory in [OUTPUT_DIR, HTML_DIR, PDF_DIR]:
        os.makedirs(directory, exist_ok=True)

def load_processed_pdfs():
    """Load the list of already processed PDFs."""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_processed_pdfs(processed_pdfs):
    """Save the list of processed PDFs."""
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(processed_pdfs, f, indent=2)

def get_pdf_links():
    """Scrape the FIA website for PDF links."""
    try:
        response = requests.get(FIA_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        pdf_links = []
        
        # Find all links that might contain PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.pdf'):
                title = link.get_text().strip()
                if not title:
                    title = os.path.basename(href)
                
                pdf_links.append({
                    'url': href if href.startswith('http') else f"https://www.fia.com{href}",
                    'title': title,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return pdf_links
    except Exception as e:
        logger.error(f"Error fetching PDF links: {e}")
        return []

def download_pdf(url, filename):
    """Download a PDF file."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading PDF {url}: {e}")
        return False

def convert_pdf_to_html(pdf_path, html_path):
    """Convert a PDF file to HTML using PyPDF2."""
    try:
        # Install PyPDF2 if not already installed
        try:
            import PyPDF2
        except ImportError:
            subprocess.run(["pip", "install", "PyPDF2"], check=True)
        
        import PyPDF2
        
        # Extract text from PDF
        pdf_text = ""
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_text += page.extract_text() + "\n\n"
        
        # Get filename for title
        pdf_filename = os.path.basename(pdf_path)
        title = pdf_filename.replace('_', ' ').replace('.pdf', '').title()
        
        # Create HTML with the extracted text
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    line-height: 1.6;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                    color: #333;
                }}
                h1 {{
                    color: #e10600;
                    text-align: center;
                    border-bottom: 2px solid #e10600;
                    padding-bottom: 10px;
                    margin-bottom: 30px;
                }}
                .pdf-content {{
                    white-space: pre-wrap;
                    font-family: monospace;
                    background-color: #f9f9f9;
                    padding: 20px;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                    overflow-x: auto;
                }}
                .pdf-viewer {{
                    margin: 30px 0;
                    text-align: center;
                }}
                .pdf-link {{
                    display: inline-block;
                    margin: 20px 0;
                    padding: 10px 20px;
                    background-color: #e10600;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .pdf-link:hover {{
                    background-color: #b30500;
                }}
                footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 0.8em;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            
            <div class="pdf-content">
                {pdf_text}
            </div>
            
            <div class="pdf-viewer">
                <h2>Original PDF Document</h2>
                <iframe src="../pdf/{pdf_filename}" width="100%" height="600px"></iframe>
            </div>
            
            <div style="text-align: center;">
                <a class="pdf-link" href="../pdf/{pdf_filename}" target="_blank">Open PDF in New Tab</a>
            </div>
            
            <footer>
                <p>Converted from PDF to HTML for easier viewing. Original document from FIA.com</p>
            </footer>
        </body>
        </html>
        """
        
        # Write HTML to file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
    except Exception as e:
        logger.error(f"Error converting PDF to HTML: {e}")
        
        # Create a simple HTML with embedded PDF viewer as fallback
        simple_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{os.path.basename(pdf_path)}</title>
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    text-align: center;
                    padding: 20px;
                    max-width: 1000px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #e10600;
                }}
                .pdf-container {{
                    margin: 20px auto;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }}
                .pdf-link {{
                    display: inline-block;
                    margin: 20px 0;
                    padding: 10px 20px;
                    background-color: #e10600;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <h1>{os.path.basename(pdf_path).replace('_', ' ').replace('.pdf', '').title()}</h1>
            <div class="pdf-container">
                <iframe src="../pdf/{os.path.basename(pdf_path)}" width="100%" height="600px"></iframe>
            </div>
            <p><a class="pdf-link" href="../pdf/{os.path.basename(pdf_path)}" target="_blank">Open PDF in new tab</a></p>
        </body>
        </html>
        """
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(simple_html)
        
        return True

def sanitize_filename(filename):
    """Sanitize a filename to be safe for file systems."""
    # Replace any non-alphanumeric characters with underscores
    return re.sub(r'[^\w\-\.]', '_', filename)

def update_index_html(processed_pdfs):
    """Update the index.html file with links to all processed PDFs."""
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FIA Formula One Documents</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }
            h1 {
                color: #e10600;
                text-align: center;
                border-bottom: 2px solid #e10600;
                padding-bottom: 10px;
            }
            p.description {
                text-align: center;
                margin-bottom: 30px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                box-shadow: 0 2px 3px rgba(0,0,0,0.1);
            }
            th, td {
                padding: 12px 15px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
                font-weight: bold;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            a {
                color: #0066cc;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            .button {
                display: inline-block;
                padding: 6px 12px;
                background-color: #e10600;
                color: white;
                border-radius: 4px;
                text-decoration: none;
            }
            .button:hover {
                background-color: #b30500;
                text-decoration: none;
            }
            .last-updated {
                text-align: center;
                margin-top: 30px;
                font-style: italic;
                color: #666;
            }
            footer {
                margin-top: 40px;
                text-align: center;
                font-size: 0.8em;
                color: #666;
                border-top: 1px solid #ddd;
                padding-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>FIA Formula One Documents Archive</h1>
        <p class="description">This page contains FIA Formula One documents converted to HTML for easier viewing.</p>
        
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Date Added</th>
                    <th>HTML Version</th>
                    <th>Original PDF</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Sort by date, newest first
    sorted_pdfs = sorted(processed_pdfs.values(), key=lambda x: x['date'], reverse=True)
    
    for pdf_info in sorted_pdfs:
        html_filename = os.path.basename(pdf_info['html_path'])
        pdf_filename = os.path.basename(pdf_info['pdf_path'])
        
        html_content += f"""
                <tr>
                    <td>{pdf_info['title']}</td>
                    <td>{pdf_info['date']}</td>
                    <td><a href="html/{html_filename}" target="_blank" class="button">View HTML</a></td>
                    <td><a href="pdf/{pdf_filename}" target="_blank" class="button">Download PDF</a></td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
        </table>
        
        <div class="last-updated">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <footer>
            <p>This is an unofficial archive of FIA Formula One documents. All documents are sourced from the official FIA website.</p>
        </footer>
    </body>
    </html>
    """
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Updated index.html with {len(processed_pdfs)} documents")

def main():
    """Main function to monitor and process PDFs."""
    logger.info("Starting FIA PDF monitor")
    
    ensure_directories()
    processed_pdfs = load_processed_pdfs()
    
    try:
        pdf_links = get_pdf_links()
        logger.info(f"Found {len(pdf_links)} PDF links")
        
        new_pdfs = 0
        
        for pdf_info in pdf_links:
            url = pdf_info['url']
            
            # Skip if already processed
            if url in processed_pdfs:
                logger.debug(f"Skipping already processed PDF: {url}")
                continue
            
            title = pdf_info['title']
            logger.info(f"Processing new PDF: {title} ({url})")
            
            # Create safe filenames
            base_filename = sanitize_filename(os.path.splitext(os.path.basename(url))[0])
            pdf_filename = f"{base_filename}.pdf"
            html_filename = f"{base_filename}.html"
            
            pdf_path = os.path.join(PDF_DIR, pdf_filename)
            html_path = os.path.join(HTML_DIR, html_filename)
            
            # Download PDF
            if download_pdf(url, pdf_path):
                logger.info(f"Downloaded PDF to {pdf_path}")
                
                # Convert to HTML
                if convert_pdf_to_html(pdf_path, html_path):
                    logger.info(f"Converted PDF to HTML: {html_path}")
                    
                    # Record as processed
                    processed_pdfs[url] = {
                        'url': url,
                        'title': title,
                        'date': pdf_info['date'],
                        'pdf_path': pdf_path,
                        'html_path': html_path
                    }
                    
                    new_pdfs += 1
                else:
                    logger.error(f"Failed to convert PDF to HTML: {pdf_path}")
            else:
                logger.error(f"Failed to download PDF: {url}")
        
        # Save processed PDFs
        save_processed_pdfs(processed_pdfs)
        
        # Update index.html
        update_index_html(processed_pdfs)
        
        logger.info(f"Processed {new_pdfs} new PDFs")
    
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == "__main__":
    main()