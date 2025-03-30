import requests
from bs4 import BeautifulSoup
import os
import json
import datetime

# Configuration
FIA_URL = "https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/"
KNOWN_PDFS_FILE = "known_pdfs.json"

def get_pdf_links():
    """Scrape the FIA website for PDF links"""
    response = requests.get(FIA_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    pdf_links = []
    # Adjust the selector based on the actual structure of the FIA website
    for link in soup.select('a[href$=".pdf"]'):
        pdf_links.append({
            'url': link['href'] if link['href'].startswith('http') else f"https://www.fia.com{link['href']}",
            'title': link.text.strip() or os.path.basename(link['href']),
            'date': datetime.datetime.now().isoformat()
        })
    
    return pdf_links

def load_known_pdfs():
    """Load the list of already processed PDFs"""
    if os.path.exists(KNOWN_PDFS_FILE):
        with open(KNOWN_PDFS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_known_pdfs(pdfs):
    """Save the updated list of processed PDFs"""
    with open(KNOWN_PDFS_FILE, 'w') as f:
        json.dump(pdfs, f, indent=2)

def find_new_pdfs():
    """Identify new PDFs that haven't been processed yet"""
    current_pdfs = get_pdf_links()
    known_pdfs = load_known_pdfs()
    
    known_urls = [pdf['url'] for pdf in known_pdfs]
    new_pdfs = [pdf for pdf in current_pdfs if pdf['url'] not in known_urls]
    
    if new_pdfs:
        known_pdfs.extend(new_pdfs)
        save_known_pdfs(known_pdfs)
    
    return new_pdfs

if __name__ == "__main__":
    new_pdfs = find_new_pdfs()
    if new_pdfs:
        print(f"Found {len(new_pdfs)} new PDFs")
        # Output the new PDFs in a format that can be used by the next step
        with open("new_pdfs.json", "w") as f:
            json.dump(new_pdfs, f, indent=2)
    else:
        print("No new PDFs found")