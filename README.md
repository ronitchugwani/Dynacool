# Dynacool Business Analytics Project

<!-- Recruiter-facing README with business context, quantified insights, and portfolio guidance. -->

## Introduction
Dynacool is a refrigeration and cooling solutions business where invoice-level sales data, customer demand patterns, and product mix directly influence planning, billing visibility, and commercial decisions. This internship project transforms raw ERP-style exports into a structured analytics workflow that supports revenue analysis, customer intelligence, forecasting, and dashboard-ready reporting.

The repository demonstrates how business data can be cleaned, analyzed, and translated into actionable insights for leadership teams instead of remaining trapped in raw Excel files.

## Problem Statement
Dynacool had access to transaction-level business data, but the reporting process was not decision-ready. Important questions such as revenue growth, seasonal demand shifts, customer concentration, invoice size patterns, and product/category contribution were difficult to answer quickly from raw exports alone.

The business need was to convert fragmented datasets into a reliable analytics pipeline that could:

- reduce manual reporting effort
- surface business trends clearly
- highlight operational inefficiencies and concentration risks
- support better planning through data-driven insights

## Objectives
- Clean and standardize messy Excel-based sales exports.
- Build a repeatable analytics pipeline for transaction-level business reporting.
- Identify revenue trends across months and years.
- Evaluate customer concentration and high-value account dependency.
- Analyze invoice value distribution and order-size behavior.
- Create business-focused visualizations for management review.
- Generate short-term revenue forecasts for planning discussions.
- Present the project in a recruiter-friendly, portfolio-ready format.

## Dataset Overview

| Dataset | Size | Type | Purpose | Key Columns |
| --- | --- | --- | --- | --- |
| `DayBook (1).xlsx` | 1,738 cleaned rows, 25 columns | Invoice-level sales transactions | Primary sales analysis | `Date`, `Particulars`, `Voucher Type`, `Voucher No`, `GSTIN/UIN`, `Gross Total`, `Sales` |
| `Master.xlsx` | 465 rows, 8 columns | Product/catalog reference sheet | Reference catalog context | `Name of Item`, `Under`, `Units`, `Opening Qty`, `Rate`, `Opening Balance` |
| `Items.csv` | 300 rows, 8 columns | Supplementary item-level sales dataset | Product/category drill-down analysis and dashboard storytelling | `Date`, `Invoice No`, `Customer`, `Item Name`, `Category`, `Quantity`, `Unit Price`, `Total Value` |

### Data Coverage
- Sales date range: `2023-01-01` to `2026-01-01`
- Customers analyzed: `899`
- Months analyzed in revenue trend: `37`

## Tools & Technologies Used
- Python
- Pandas
- NumPy
- Matplotlib
- Statsmodels
- OpenPyXL
- FastAPI
- Streamlit
- React + Vite
- Tailwind CSS
- Plotly
- Excel / CSV data sources

## Methodology
1. Loaded raw DayBook and reference files from Excel exports.
2. Recovered misplaced header rows automatically from ERP-style report formats.
3. Normalized column names and converted numeric/text fields into analysis-ready formats.
4. Cleaned missing values, validated date and revenue columns, and created time features.
5. Ran exploratory data analysis on revenue, customer behavior, seasonality, and order-size distribution.
6. Generated business visuals including revenue trend, Pareto analysis, product mix, and forecast plots.
7. Built a six-month ARIMA-based revenue forecast for forward-looking planning.
8. Exported results into reusable outputs for dashboards, reporting, and portfolio presentation.

## Key Insights

### 1. Strong Revenue Scale With Clear Growth Momentum
- Total gross billed value analyzed: `240.55M`
- Net sales value identified from the dataset: `201.10M`
- Revenue grew from `70.05M` in 2023 to `74.48M` in 2024, then accelerated to `95.74M` in 2025.
- 2025 delivered approximately `28.5%` year-over-year growth over 2024, indicating a strong expansion phase in the business.

### 2. Seasonality Is Visible and Useful for Planning
- The highest single billing month in the dataset was `March 2025` with `13.71M`.
- Across the full timeline, `March` was the strongest calendar month, while `April` and `May` were relatively softer.
- This pattern can support better pre-season inventory planning, manpower allocation, and targeted sales pushes before weaker months.

### 3. Customer Base Is Broad, Which Reduces Dependency Risk
- The project identified `899` unique customers.
- The top 10 customers contributed only `18.85%` of total revenue.
- It took `215` customers to account for 80% of overall revenue, which suggests Dynacool is not overly dependent on a very small set of accounts.
- From a business risk perspective, this indicates a diversified customer base, though it also implies a need for strong account coverage and service consistency.

### 4. The Business Has a Mix of Routine and High-Value Orders
- Average invoice value: `138.41K`
- Median invoice value: `65.00K`
- The large gap between average and median invoice value shows that a smaller number of high-ticket orders materially lift overall revenue.
- Around `16%` of transactions were above `200K`, which signals a lumpy demand profile that finance and operations teams should plan around.

### 5. Invoice Components Matter for Commercial Tracking
- The difference between gross billed value and net sales was `39.45M`.
- That gap represents about `16.4%` of gross invoice value.
- This is important because commercial teams often track topline billing, while finance teams monitor the net sales base more closely. A structured split improves margin, tax, and cash-flow discussions.

### 6. Product Mix Is Concentrated Around Equipment
- In the supplementary item-level analysis, `Equipment` contributed `62.72%` of item sales value.
- `Compressor Unit` alone contributed `34.66%`, and the top 3 items together contributed `79.29%`.
- This suggests procurement and stock planning should prioritize high-value equipment lines, while consumables and electronics can be managed with leaner replenishment logic.

## Results / Impact
- Converted raw business exports into a repeatable analytics workflow instead of a one-time spreadsheet exercise.
- Automatically recovered misplaced headers and cleaned the sales file into `1,738` usable records.
- Produced a reusable analysis output file at [`outputs/results/analysis_results.json`](outputs/results/analysis_results.json).
- Generated portfolio-ready charts in [`outputs/plots`](outputs/plots).
- Built a six-month baseline forecast, with the next forecasted month (`2026-02`) estimated at about `7.62M`.
- Added product/category storytelling so the project demonstrates both technical analytics skills and commercial thinking.

## Visualizations
The project now generates business-relevant charts such as:

- Monthly revenue trend with 3-month moving average
- Year-wise revenue comparison
- Seasonality by calendar month
- Top customers by revenue
- Customer Pareto analysis
- Revenue distribution histogram
- Gross invoice value vs net sales comparison
- Item-level sales trend
- Revenue by product category
- Top items by sales value
- ARIMA revenue forecast

## Suggested Screenshots
To make the repository stand out on GitHub, save screenshots inside an `images/` folder and place them in the README in this order:

### 1. Executive Overview
Place this directly below the introduction to give recruiters a fast visual entry point.

```md
![Dashboard Overview](images/dashboard-overview.png)
```

### 2. Revenue Trend
Place this under the **Visualizations** section.

```md
![Monthly Revenue Trend](images/monthly-revenue-trend.png)
```

### 3. Customer Pareto
Place this under **Key Insights** after the customer concentration discussion.

```md
![Customer Pareto](images/customer-pareto.png)
```

### 4. Product Mix / Category Chart
Place this under **Results / Impact** to show business breadth beyond pure sales totals.

```md
![Category Revenue](images/category-revenue.png)
```

### 5. Revenue Forecast
Place this near the end of the README before **Conclusion**.

```md
![Revenue Forecast](images/revenue-forecast.png)
```

## Recommended Screenshot Sources
- `outputs/plots/monthly_revenue_trend.png`
- `outputs/plots/customer_pareto.png`
- `outputs/plots/category_revenue.png`
- `outputs/plots/revenue_forecast_arima.png`
- Frontend dashboard home screen from the React dashboard

## Conclusion
This project shows how raw operational data can be converted into a business analytics solution that is useful for management, understandable to non-technical stakeholders, and strong enough for a professional portfolio. It highlights not only technical execution in Python and analytics tooling, but also the ability to interpret commercial patterns, communicate insights clearly, and connect data work to business decisions.

## Future Scope
- Integrate the product catalog directly with transaction-level item data from the ERP for deeper SKU-level profitability analysis.
- Add margin, repeat-customer, and churn-style commercial KPIs.
- Deploy the FastAPI + React dashboard for live business reporting.
- Introduce anomaly detection for unusually high or low invoice behavior.
- Improve forecasting with model comparison, backtesting, and confidence-based scenario planning.

## How To Run

### Analytics Pipeline
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Streamlit Dashboard
```bash
cd backend
streamlit run app.py
```

### FastAPI Backend
```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 10000
```

### React Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment Notes

### Vercel
Deploy the `frontend/` app only.

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_URL=https://your-backend-url.onrender.com`

### Render
Deploy the `backend/` app as a Python web service.

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn api:app --host 0.0.0.0 --port 10000`

## Repository Structure
```text
dynacool/
+-- backend/
|   +-- api.py
|   +-- backend_api.py
|   +-- data_cleaning.py
|   +-- data_integration.py
|   +-- eda.py
|   +-- forecasting.py
|   +-- item_analytics.py
|   +-- main.py
|   +-- app.py
|   +-- requirements.txt
|   +-- render.yaml
|   +-- data/
|       +-- DayBook (1).xlsx
|       +-- Master.xlsx
|       +-- Items.csv
+-- outputs/
+-- frontend/
|   +-- .env
|   +-- package.json
|   +-- vite.config.js
|   +-- vercel.json
```
