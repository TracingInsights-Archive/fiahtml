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
import xml.etree.ElementTree as ET

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
GROBID_DIR = "grobid"
GROBID_PORT = 8070

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

def setup_grobid():
    """Setup GROBID if not already installed."""
    if not os.path.exists(GROBID_DIR):
        logger.info("Setting up GROBID...")
        # Clone GROBID repository
        subprocess.run(["git", "clone", "https://github.com/kermitt2/grobid.git", GROBID_DIR], check=True)
        
        # Change to GROBID directory
        os.chdir(GROBID_DIR)
        
        # Build GROBID (requires Gradle)
        subprocess.run(["./gradlew", "clean", "install"], check=True)
        
        # Return to original directory
        os.chdir("..")
        
        logger.info("GROBID setup complete")

def start_grobid_service():
    """Start the GROBID service."""
    logger.info("Starting GROBID service...")
    
    # Change to GROBID directory
    os.chdir(GROBID_DIR)
    
    # Start GROBID service
    process = subprocess.Popen(["./gradlew", "run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Return to original directory
    os.chdir("..")
    
    # Wait for service to start
    time.sleep(30)
    
    # Check if service is running
    try:
        response = requests.get(f"http://localhost:{GROBID_PORT}")
        if response.status_code == 200:
            logger.info("GROBID service started successfully")
            return process
        else:
            logger.error(f"GROBID service returned status code {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error checking GROBID service: {e}")
        return None

def stop_grobid_service(process):
    """Stop the GROBID service."""
    if process:
        logger.info("Stopping GROBID service...")
        process.terminate()
        process.wait()
        logger.info("GROBID service stopped")

def convert_pdf_to_html_with_grobid(pdf_path, html_path):
    """Convert a PDF file to HTML using GROBID."""
    try:
        # Process PDF with GROBID
        url = f"http://localhost:{GROBID_PORT}/api/processFulltextDocument"
        with open(pdf_path, 'rb') as pdf_file:
            response = requests.post(url, files={'input': pdf_file})
        
        if response.status_code != 200:
            logger.error(f"GROBID processing failed with status code {response.status_code}")
            return False
        
        # Parse the TEI XML response
        tei_xml = response.text
        
        # Convert TEI XML to HTML
        html_content = tei_to_html(tei_xml, os.path.basename(pdf_path))
        
        # Write HTML to file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
    except Exception as e:
        logger.error(f"Error converting PDF to HTML with GROBID: {e}")
        return False

def tei_to_html(tei_xml, pdf_name):
    """Convert TEI XML to HTML."""
    try:
        # Parse XML
        root = ET.fromstring(tei_xml)
        
        # Extract title
        title_elem = root.find(".//titleStmt/title")
        title = title_elem.text if title_elem is not None else pdf_name
        
        # Extract abstract
        abstract_elem = root.find(".//abstract")
        abstract = ""
        if abstract_elem is not None:
            abstract = ET.tostring(abstract_elem, encoding='unicode', method='text')
        
        # Extract body text
        body_elem = root.find(".//body")
        body_text = ""
        if body_elem is not None:
            body_text = ET.tostring(body_elem, encoding='unicode', method='text')
        
        # Create HTML
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                    text-align: center;
                }}
                .abstract {{
                    font-style: italic;
                    margin-bottom: 20px;
                    padding: 10px;
                    background-color: #f5f5f5;
                }}
                .content {{
                    text-align: justify;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="abstract">
                <strong>Abstract:</strong> {abstract}
            </div>
            <div class="content">
                {body_text}
            </div>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        logger.error(f"Error converting TEI to HTML: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Processing {pdf_name}</title>
        </head>
        <body>
            <h1>Error Processing Document</h1>
            <p>There was an error processing this document with GROBID.</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """

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
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
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
            .last-updated {
                text-align: center;
                margin-top: 20px;
                font-style: italic;
                color: #666;
            }
        </style>
    </head>
    <body>
        <h1>FIA Formula One Documents</h1>
        <p>This page contains converted FIA Formula One documents for easier viewing.</p>
        
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
                    <td><a href="html/{html_filename}" target="_blank">View HTML</a></td>
                    <td><a href="pdf/{pdf_filename}" target="_blank">Download PDF</a></td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
        </table>
        
        <div class="last-updated">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
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
    
    # Setup and start GROBID
    setup_grobid()
    grobid_process = start_grobid_service()
    
    if not grobid_process:
        logger.error("Failed to start GROBID service. Exiting.")
        return
    
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
                
                # Convert to HTML using GROBID
                if convert_pdf_to_html_with_grobid(pdf_path, html_path):
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
    
    finally:
        # Stop GROBID service
        stop_grobid_service(grobid_process)

if __name__ == "__main__":
    main()