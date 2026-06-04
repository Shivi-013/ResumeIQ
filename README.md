# ResumeIQ — AI Resume Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-Google-4285F4?style=for-the-badge&logo=google&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

**Upload your resume. Paste a job description. Get an AI-powered match report in seconds.**

[Live Demo](#deployment) · [Features](#features) · [Quick Start](#quick-start) · [API Reference](#environment-variables)

</div>

---

## Overview

ResumeIQ is a full-stack web application that helps job seekers understand exactly how well their resume matches a target job description. It extracts text from your PDF resume, sends it to Google Gemini for deep analysis, and returns a comprehensive report covering ATS compatibility, missing skills, improvement suggestions, interview preparation questions, a learning roadmap, and more.

---

## Features

### Core Analysis
| Feature | Description |
|---|---|
| **ATS Score** | How well your resume passes Applicant Tracking Systems |
| **Match Score** | Overall match plus individual scores for Skills, Experience, and Education |
| **Skills Gap** | Side-by-side view of required, found, and missing skills |
| **Keyword Coverage** | Visual bar showing how often each required keyword appears in your resume |
| **Semantic Similarity** | Cosine similarity score between resume and JD using sentence-transformers |

### AI-Powered Insights (Gemini)
| Feature | Description |
|---|---|
| **Strengths & Weaknesses** | What your resume does well vs. where it falls short for this specific role |
| **Improvement Suggestions** | Concrete, actionable steps to close the gap |
| **Bullet Point Rewriter** | AI rewrites your weak bullets with stronger action verbs and quantified impact |
| **Section Audit** | Keep / Remove / Add / Improve recommendations for each resume section |
| **Interview Questions** | 10 personalized questions — Technical, Behavioral, Project-Based, Scenario-Based |
| **Learning Roadmap** | Week-by-week plan to acquire missing skills |
| **Company Match** | Evaluate your resume against Google, Amazon, Microsoft, Netflix, or Meta's hiring bar |

### Additional Tools
| Feature | Description |
|---|---|
| **PDF Report** | Download a professional multi-page PDF of your full analysis |
| **Resume Comparison** | Upload two resume versions and see which scores better (A/B test) |
| **Dark Mode** | Persistent dark/light toggle stored in localStorage |

---

## Screenshots

```
Landing Page  →  Analyzer  →  Results Dashboard  →  PDF Download
                                    │
                         ┌──────────┼──────────────┐
                     Overview   AI Insights   Improvements   Company Match
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10 · Flask 3.1 · Gunicorn |
| **AI** | Google Gemini (gemini-2.5-flash via `google-generativeai`) |
| **PDF Parsing** | PyPDF 5 |
| **Semantic Similarity** | `sentence-transformers` · `all-MiniLM-L6-v2` |
| **PDF Generation** | ReportLab 4.2 |
| **Frontend** | Tailwind CSS (Play CDN) · Chart.js (CDN) · Vanilla JS |
| **Deployment** | Render · `render.yaml` |

---

## Project Structure

```
resumeiq/
├── app.py                     # Flask factory — creates app, registers blueprints
├── config.py                  # Dev / Prod config classes
│
├── routes/
│   ├── analyzer.py            # POST /analyze — full V2 pipeline; GET /results
│   ├── company.py             # POST /company-analyze — AJAX company match
│   ├── compare.py             # GET/POST /compare — A/B resume comparison
│   ├── main.py                # GET / — landing page
│   └── report.py              # GET /report/download — PDF download
│
├── services/
│   ├── gemini_service.py      # Gemini API — V2 prompt, response parser
│   ├── resume_parser.py       # PyPDF text extraction + cleaning
│   ├── job_analyzer.py        # Keyword extraction, overlap scoring, coverage
│   ├── semantic_service.py    # Sentence-transformers cosine similarity
│   ├── report_generator.py    # ReportLab PDF builder
│   └── company_service.py     # Company profiles + Gemini prompts
│
├── utils/
│   └── validators.py          # PDF (magic bytes + ext) and JD validation
│
├── templates/
│   ├── base.html              # Shared nav, footer, dark mode, flash messages
│   ├── index.html             # Landing page — hero, features, how it works
│   ├── analyzer.html          # Upload form + JD textarea
│   ├── results.html           # Tabbed results dashboard
│   └── compare.html           # A/B comparison page
│
├── static/
│   ├── css/custom.css         # Gradients, card styles, chips, animations
│   └── js/
│       ├── main.js            # Dark mode toggle, smooth scroll
│       ├── upload.js          # Drag-and-drop upload, character counter
│       └── charts.js          # Chart.js — Bar, Doughnut
│
├── uploads/                   # Ephemeral PDF storage (deleted after parsing)
├── reports/                   # Analysis JSON files (auto-cleaned after 2 hours)
│
├── requirements.txt
├── Procfile                   # gunicorn app:app
├── render.yaml                # Render deployment config
└── .env.example               # Environment variable reference
```

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- A **Google Gemini API key** — get one free at [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/resumeiq.git
cd resumeiq
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` pulls in PyTorch (~1.5 GB). First install takes a few minutes. The `all-MiniLM-L6-v2` model (~90 MB) is downloaded on first use.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
FLASK_ENV=development
SECRET_KEY=your-long-random-secret-key-here
GEMINI_API_KEY=your-gemini-api-key-here
```

### 5. Run the development server

```bash
python app.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **Yes** | Flask session secret — use a long random string in production |
| `GEMINI_API_KEY` | **Yes** | Your Google Gemini API key |
| `FLASK_ENV` | No | `development` (default) or `production` |

---

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  PDF Upload  │────▶│  PyPDF Extractor  │────▶│  resume_text (str)  │
└─────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                          │
┌──────────────────────────────────────────────────────────────────┐
│                         Analysis Pipeline                          │
│                                                                    │
│  resume_text + jd_text                                            │
│       │                                                            │
│       ├──▶  Gemini API  ──▶  JSON (scores, skills, questions,    │
│       │                       roadmap, bullet rewrites, audit)    │
│       │                                                            │
│       ├──▶  sentence-transformers  ──▶  semantic_score (0–100)   │
│       │                                                            │
│       └──▶  keyword_coverage()  ──▶  strong / medium / missing   │
│                                                                    │
└────────────────────────┬─────────────────────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │  reports/{uuid}.json   │  ◀── session stores report_id
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │   results.html         │  tabbed SaaS dashboard
              └────────────────────────┘
```

**Why file-based report storage?**
The V2 analysis payload (interview questions, roadmap, section audit, bullet rewrites) can exceed the 4 KB Flask session cookie limit. Reports are saved to `reports/` as JSON files; only the UUID is stored in the session. Files are auto-deleted after 2 hours.

---

## Fallback Mode

If `GEMINI_API_KEY` is not configured or the API call fails, ResumeIQ falls back to **local keyword-overlap scoring**. You will see a yellow warning banner on the results page. In fallback mode:

- Scores are based on keyword frequency matching (no deep analysis)
- Interview questions, learning roadmap, bullet rewrites, and section audit show placeholder content
- The PDF report and A/B comparison still work

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  Built with Flask &amp; Google Gemini AI &nbsp;·&nbsp; <strong>ResumeIQ</strong>
</div>
