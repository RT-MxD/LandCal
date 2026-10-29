# 🌾 LandCal — Land Calculation LangGraph Workflow

A Python application and workflow built with **LangGraph** designed to automate and simplify land calculation, metric conversions, and payment milestone tracking.

---

## 📋 Features & Layout Structure

The workflow follows a structured 6-row arrangement:

1. **Row 1 (Location Variables)**:
   - `District`
   - `Taluka`
   - `Village`

2. **Row 2 (Land Survey & Metrics)**:
   - `Old Survey No`
   - `New Survey No`
   - `Area` (Base input)
   - `Bigha` (Formula: `area / 16`)
   - `Sq.mt` (Formula: `area / 1618.74`)
   - `Sq.yd` (Formula: `area / 1936`)
   - *Auto-calculates dynamically while allowing manual user overrides.*

3. **Row 3 (Rate & Valuations)**:
   - `Valuation per Bigha` (Manually entered by user)
   - `Valuation per Sq.yd` (Manually entered by user)

4. **Row 4 (Parties Involved)**:
   - `Buyer Name`
   - `Seller Name`
   - `Broker`

5. **Row 5 (Transaction & Timeline)**:
   - `Total Payment`
   - `Buy Date`
   - `Condition`
   - `Last Payment Date`
   - `Sell Date`

6. **Row 6 (Conditions beside Rupees)**:
   - Dynamic table of payment conditions/milestones beside their respective rupee amounts.
   - Calculates total payments committed under conditions and remaining balance.

7. **Row 7 (Land Photos Uploader)**:
   - Survey-locked photo attachments avoiding cross-survey mismatches.

8. **Section 2 (Saved Reports Explorer)**:
   - Search, filter, and inspect reports stored in PostgreSQL specifically by **New Survey No**.
   - Review complete financial and legal milestone details, reload saved reports into the calculator, and download markdown summaries.

---

## 🗄️ Database Setup (PostgreSQL)

LandCal can automatically store generated reports into a local PostgreSQL database.

1. Open or create your `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://postgres:password@localhost:5432/landcal
   ```
2. If `DATABASE_URL` is empty, calculations run normally without database persistence.
3. Tables and indices are automatically initialized upon the first report save.

---

## 📦 Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

### 1. Interactive Web Application (Streamlit)
Launch the interactive web UI matching the 6-row layout:

```bash
streamlit run landcal_application.py
```

### 2. FastAPI REST API Server
Launch the FastAPI REST API with automatic docs and live reloading:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### Key REST Endpoints:
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status, version, and documentation links |
| `GET` | `/api/health` | PostgreSQL database connectivity and health check |
| `POST` | `/api/convert-metrics` | Quick area metrics conversion (`Bigha`, `Sq.mt`, `Sq.yd`) |
| `POST` | `/api/calculate` | Execute full LangGraph calculation & deal report generation |
| `GET` | `/api/reports` | List saved reports (filter by `new_survey_no`, `limit`) |
| `GET` | `/api/reports/{id}` | Retrieve full report by record ID |
| `PUT` | `/api/reports/{id}` | Update existing report with new values/payments |
| `DELETE` | `/api/reports/{id}` | Delete report from PostgreSQL |
| `GET` | `/api/reports/{id}/markdown` | Download deal Markdown summary report |
| `GET` | `/api/reports/export/csv` | Download CSV backup spreadsheet of all saved reports |
| `POST` | `/api/photos/upload` | Upload inspection photos locked to a Survey Number |
| `GET` | `/api/photos` | List photos for a survey number (or old + new survey) |
| `GET` | `/api/photos/file/{survey}/{file}` | Stream and view attached photo file directly |
| `DELETE` | `/api/photos` | Delete an attached inspection photo |

### 3. Command Line Interface (CLI)
Run a calculation directly from terminal:

```bash
python cli.py
```

Or pass custom parameters:

```bash
python cli.py --district "Vadodara" --taluka "Padra" --village "Samiyala" --area 1600 --rate-bigha 1000000 --total-payment 100000000
```

### 4. Programmatic Usage in Python
You can import the compiled LangGraph workflow anywhere in your code:

```python
from land_graph import run_land_calculation

result = run_land_calculation({
    "district": "Ahmedabad",
    "taluka": "Sanand",
    "village": "Shela",
    "old_survey_no": "104/A",
    "new_survey_no": "112",
    "area": 3200.0,
    "rupees_per_bigha": 2500000.0,
    "rupees_per_sq_yd": 12000.0,
    "buyer_name": "Ramesh Patel",
    "seller_name": "Kishore Shah",
    "broker": "Mahesh Desai",
    "total_payment": 5000000.0,
    "buy_date": "2026-03-01",
    "condition": "Title Clearance",
    "last_payment_date": "2026-06-30",
    "sell_date": "2026-07-15",
    "conditions_list": [
        {"condition": "Token Advance", "rupees": 500000.0},
        {"condition": "Banakhat / Agreement", "rupees": 1500000.0},
        {"condition": "Dastavej (Final Registry)", "rupees": 3000000.0},
    ],
})

print(result["summary_report"])
```

---

## 🧪 Running Unit Tests

Run the full test suite with:

```bash
pytest tests/ -v
```
