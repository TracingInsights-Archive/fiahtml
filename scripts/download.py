import requests
import os
import json
import time
from urllib.parse import urlparse

# Configuration
DOWNLOAD_DIR = "downloads"

def ensure_dir(directory):
    """Ensure the directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_pdf(pdf_info):
    """Download a PDF file"""
    url = pdf_info['url']
    filename = os.path.basename(urlparse(url).path)
    
    # Create a sanitized filename from the title if available
    if pdf_info.get('title'):
        sanitized_title = "".join([c if c.isalnum() or c in [' ', '.', '-', '_'] else '_' for c in pdf_info['title']])
        filename = f"{sanitized_title}.pdf"
    
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    
    print(f"Downloading {url} to {filepath}")
    
    # Download with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Update the PDF info with the local path
            pdf_info['local_path'] = filepath
            return pdf_info
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
            else:
                print(f"Failed to download {url} after {max_retries} attempts")
                return None

def download_new_pdfs():
    """Download all new PDFs"""
    ensure_dir(DOWNLOAD_DIR)
    
    if not os.path.exists("new_pdfs.json"):
        print("No new PDFs to download")
        return []
    
    with open("new_pdfs.json", "r") as f:
        new_pdfs = json.load(f)
    
    downloaded_pdfs = []
    for pdf_info in new_pdfs:
        result = download_pdf(pdf_info)
        if result:
            downloaded_pdfs.append(result)
    
    # Save the downloaded PDFs info
    with open("downloaded_pdfs.json", "w") as f:
        json.dump(downloaded_pdfs, f, indent=2)
    
    return downloaded_pdfs

if __name__ == "__main__":
    downloaded = download_new_pdfs()
    print(f"Downloaded {len(downloaded)} PDFs")