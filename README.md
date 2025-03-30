# FIA PDF to HTML Converter

This project automatically monitors the FIA website for new PDF documents, converts them to HTML using GROBID, and publishes them to GitHub Pages.

## How It Works

1. A GitHub Actions workflow runs on a schedule (hourly by default)
2. The workflow checks the FIA website for new PDF documents
3. New PDFs are downloaded and converted to HTML using GROBID
4. The HTML files are published to GitHub Pages

## Viewing the Documents

The converted documents are available at: https://tracinginsights-archive.github.io/fiahtml/

## Manual Trigger

You can manually trigger the conversion process by:
1. Going to the "Actions" tab in the repository
2. Selecting the "PDF to HTML Converter" workflow
3. Clicking "Run workflow"

## Local Development

To run the scripts locally:

1. Install dependencies:
pip install requests beautifulsoup4 lxml

2. Run the scripts in sequence:
python scripts/monitor.py
python scripts/download.py

3. For the conversion step, you'll need Docker installed:
docker run --rm -d --name grobid -p 8070:8070 lfoppiano/grobid:0.7.2
python scripts/convert.py

## Technology

This project uses GROBID (GeneRation Of BIbliographic Data), which is the same technology used by arXiv.org for converting scientific papers to HTML. GROBID provides better structure recognition and semantic understanding of documents compared to other PDF to HTML converters.