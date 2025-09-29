# DoJ J-Book Technology Relevance Analyzer

A Python tool for extracting, enriching, and analyzing DoD budget documents (J-Books) to identify technology-relevant programs. Combines PDF parsing, Excel integration, AI-powered relevance tagging, and an interactive Streamlit dashboard for budget analysis and filtering.

## Key Features

- **PDF + Excel Data Fusion**: Extracts and combines data from J-Book PDFs and Excel files
- **AI-Powered Relevance Scoring**: Uses OpenAI API to automatically tag programs for custom keywords (e.g., C-UAS, hypersonics)
- **Interactive Web Dashboard**: Streamlit-based interface for filtering, tagging, and analysis
- **Weighted Budget Calculations**: Calculates budget totals weighted by technology relevance
- **Export Capabilities**: Download processed data for further analysis

## Tech Stack

- **Python 3.9+**
- **Streamlit** - Interactive web dashboard
- **OpenAI API** - AI-powered relevance tagging
- **PyMuPDF** - PDF text extraction
- **pandas** - Data processing and analysis
- **openpyxl** - Excel file processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ValenteMendez/doj-jbook-ow.git
cd doj-jbook-ow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install in development mode:
```bash
pip install -e .
```

4. Set up environment variables:
```bash
cp .env.example .env
# Add your OpenAI API key to .env
```

## Quick Start

1. **Prepare your data structure**:
```
data/
├── FY25 - PDFs to be Uploaded/
│   └── RDTE_OSD_FY2025.pdf
├── FY25 - addt. excel files/
│   └── RDTE_OSD_FY2025_Exhibit_R-1D.xlsx
└── processed/
```

2. **Run the complete pipeline**:
```bash
# Define paths
PDF="data/FY25 - PDFs to be Uploaded/RDTE_OSD_FY2025.pdf"
XLSX="data/FY25 - addt. excel files/RDTE_OSD_FY2025_Exhibit_R-1D.xlsx"
OUT="data/processed/test_osd_enriched.csv"
TAGGED="data/processed/test_osd_enriched_tagged.csv"

# Build enriched CSV (PDF + Excel)
python -m doj_jbook.cli.pipeline --pdf "$PDF" --xlsx "$XLSX" --use-r1d-description --out "$OUT"

# Tag with OpenAI
python -m doj_jbook.cli.tagging --input "$OUT" --output "$TAGGED" --keywords C-UAS hypersonics --provider openai --model gpt-4o-mini --concurrency 4 --env-file .env

# Launch Streamlit dashboard
streamlit run app/streamlit_app.py -- --input "$TAGGED" --weights "High=1.0,Medium=0.5,Low=0.1"
```

## Usage

### Command Line Interface

The tool provides two main CLI commands:

#### Pipeline Command
Extract and enrich data from PDF and Excel sources:
```bash
python -m doj_jbook.cli.pipeline \
    --pdf path/to/budget.pdf \
    --xlsx path/to/exhibit.xlsx \
    --use-r1d-description \
    --out output.csv
```

#### Tagging Command
Apply AI-powered relevance tagging:
```bash
python -m doj_jbook.cli.tagging \
    --input enriched.csv \
    --output tagged.csv \
    --keywords "C-UAS hypersonics" \
    --provider openai \
    --model gpt-4o-mini \
    --concurrency 4 \
    --env-file .env
```

### Streamlit Dashboard

Launch the interactive dashboard:
```bash
streamlit run app/streamlit_app.py -- --input tagged_data.csv --weights "High=1.0,Medium=0.5,Low=0.1"
```

Features:
- **Weighted Budget Totals**: Automatically calculated based on relevance scores
- **Interactive Filtering**: Filter by PE number, project name, cost category, or keywords
- **Manual Tagging**: Override AI tags or tag filtered subsets
- **Row-by-Row Editing**: View and edit individual program details
- **Export**: Download processed data as CSV

## Configuration

### Environment Variables
Create a `.env` file with:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Weighting System
Configure relevance weights when launching Streamlit:
- `High=1.0` - Full budget weight for highly relevant programs
- `Medium=0.5` - Half weight for moderately relevant programs  
- `Low=0.1` - Minimal weight for low relevance programs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
