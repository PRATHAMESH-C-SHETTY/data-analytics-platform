# ⚡ DataLens — Smart Data Analytics Platform

A fully professional, automated data analytics platform with dark/light mode,
real-time dashboard charts, live report generation stored in the Reports section,
Plotly interactive visualizations, and complete auth system.

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt

# Run
python app.py
# → http://localhost:5055
```

**Demo account:** `demo@datalens.io` / `datalens123`

## ✨ Features

| Feature | Detail |
|---|---|
| **Dark + Light mode** | Toggle button in navbar, persists via localStorage |
| **Real-time dashboard** | Live charts (activity & file types) auto-refresh every 30s |
| **Schema-agnostic upload** | CSV, Excel, JSON — any structure, any columns |
| **Auto analysis** | Numeric/categorical/datetime detection, descriptive stats |
| **11 chart types** | Histograms, box plots, scatter, pie, bar, heatmap, line, grouped bar |
| **Insight engine** | Skewness, variability, correlation, data quality alerts |
| **PDF reports** | ReportLab — full stats tables, insights, data sample |
| **Excel reports** | openpyxl — 5 sheets with charts, stats, insights |
| **Reports stored** | All reports saved in `/reports`, listed in Reports page |
| **Auth system** | Register, login, profile, per-user data isolation |
| **Search / filter** | Tables have live search in Datasets and Reports pages |

## 📂 Structure

```
datalens/
├── app.py                    # Flask routes + SQLAlchemy models
├── requirements.txt
├── templates/
│   ├── base.html             # CSS design system + dark/light theme + navbar
│   ├── dashboard.html        # Real-time charts + live stats
│   ├── upload.html           # Drag-drop upload
│   ├── preview.html          # Column types, data sample
│   ├── analyze.html          # Full analysis: charts, stats, insights, export
│   ├── reports.html          # Reports list with download
│   ├── datasets.html         # Dataset management
│   ├── login.html
│   ├── signup.html           # Password strength meter
│   └── profile.html
└── utils/
    ├── data_engine.py        # Load, inspect, clean
    ├── analytics_engine.py   # Statistics, correlations
    ├── viz_engine.py         # 11 Plotly chart types
    ├── insight_engine.py     # Automated insights
    └── report_engine.py      # PDF + Excel generation
```

## 🔄 Workflow

**Dashboard → Upload → Preview → Analysis → Charts/Stats/Insights → Export PDF/Excel → Reports**
