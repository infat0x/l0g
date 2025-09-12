# Log Analysis CTI — README (Teacher Copy)

> ⚡ **Recommended:** Run the packaged **EXE** for fastest testing. No setup required.

**Test user credentials:**
```
user: test
password: salam123
```

## 📺 Usage Video
[![Usage Demo](https://img.youtube.com/vi/nCyLXXgXqCw/0.jpg)](https://youtu.be/nCyLXXgXqCw)

---

## 1) What this tool does
- **Parses logs**: Apache/Nginx combined, JSON Lines/Array, CSV/TSV.
- **Analyzes traffic**: per‑IP counters, HTTP methods/statuses, top paths.
- **CTI Enrichment**: For each unique IP, query **VirusTotal** + **AbuseIPDB**.
- **Per‑user tokens**: Each user sets tokens in **Settings** or via `.env`.
- **Interactive details**: Click any scanned IP → see more info/links.
- **History**: View old lookups and reuse cached results offline.
- **Reports**: Export Markdown/HTML/TXT; PDF if optional deps are present.

---

## 2) Project layout (updated)
```
C:\Users\Student\Desktop\log_analysis_cti
├── .env                          # user tokens (DO NOT SHARE)
├── .venv/                        # virtual environment (optional)
├── README.md                     # this file
├── src/                          # source code (package)
│   └── log_analysis_cti/
│       ├── __init__.py
│       ├── gui_app.py            # GUI entry (python -m log_analysis_cti.gui_app)
│       ├── main.py               # CLI entry (python -m log_analysis_cti.main)
│       ├── ai_client.py
│       ├── behavior_analyzer.py
│       ├── config.py
│       ├── file_validator.py
│       ├── log_parser.py
│       ├── report_generator.py   # writes to out/reports by default
│       ├── assets/
│       │   └── l0g_dark_green.ico
│       └── cti_apis/
│           ├── __init__.py
│           ├── abuseipdb.py
│           ├── virustotal.py
│           └── cti_manager.py
├── scripts/
│   └── packaging/
│       ├── build_exe.py          # builds using log_analysis_cti.spec
│       ├── log_analysis_cti.spec # PyInstaller spec (points to src/.../gui_app.py)
│       ├── setup.py              # helper setup script
│       └── requirements.txt      # dependencies
└── out/
    ├── build/                    # PyInstaller build artifacts
    ├── dist/                     # LogAnalysisCTI.exe output
    └── reports/                  # generated reports (runtime)
```

---


## 3) Quick start (Windows)
> **Preferred:** Run the **EXE** build.

### Option A — Run the packaged EXE ✅
1. Double‑click:
   ```
   C:\Users\Student\Desktop\log_analysis_cti\out\dist\LogAnalysisCTI.exe
   ```
2. Login with test account (above).
3. Go to **Settings → API Keys** and paste your tokens.
4. **Open Log** → select a file; click **Analyze** → click any IP for details.
5. Use **History** to view old lookups; **Export** reports as needed.

### Option B — Run from source (venv)
```powershell
cd C:\Users\Student\Desktop\log_analysis_cti
. .venv\Scripts\Activate.ps1
pip install -U pip
pip install -r .\scripts\packaging\requirements.txt

# GUI
python -m log_analysis_cti.gui_app

# or CLI
python -m log_analysis_cti.main <log_file_path>
```

---

## 4) Configure tokens (per user)
Create/edit **`.env`** in the project root:
```dotenv
VT_API_KEY=your_virustotal_key_here
ABUSEIPDB_API_KEY=your_abuseipdb_key_here
XAI_API_KEY=your_xai_grok_key_here  # optional
```

Or set them in‑app: **Settings → API Keys**. Each user keeps their own tokens.

---

## 5) Using the app (flow)
1. **Login** with provided test user.
2. **Open Log** → choose format (auto‑detected):
   - Combined (Apache/Nginx)
   - JSONL/JSON
   - CSV/TSV
3. **Analyze** → per‑IP stats + highlight suspicious UAs.
4. **Click an IP** → view VT + AbuseIPDB details.
5. **History** → reuse cached results.
6. **Export** report (MD/HTML/TXT/PDF).

---

## 6) Notes
- The EXE is the easiest way to test (no Python setup needed).
- Tokens must be set for enrichment features.
- `.env` is ignored by version control for safety.
- Reports are saved under `out/reports/` by default.

---

## 8) Build the EXE (optional)
```powershell
cd C:\Users\Student\Desktop\log_analysis_cti
python .\scripts\packaging\build_exe.py

# Output:
# - out\dist\LogAnalysisCTI.exe
# - out\LogAnalysisCTI_Standalone\ (ready to share)
```

---

## 7) Security
- Keep `.env` private.
- Do not share tokens in screenshots.
- Respect VirusTotal/AbuseIPDB usage policies.

