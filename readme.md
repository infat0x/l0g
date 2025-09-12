# Log Analysis CTI 🔍

> ⚡ **Cyber Threat Intelligence Tool** for log analysis and IP reputation checking

[![GitHub](https://img.shields.io/badge/GitHub-infat0x%2Fl0g-blue?style=flat-square&logo=github)](https://github.com/infat0x/l0g)
[![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

**Test user credentials:**
```
user: test
password: salam123
```

## 📺 Usage Video
[![Usage Demo](https://img.youtube.com/vi/nCyLXXgXqCw/0.jpg)](https://youtu.be/nCyLXXgXqCw)

---

## ✨ Features

- 🔍 **Log Parsing**: Apache/Nginx combined, JSON Lines/Array, CSV/TSV
- 📊 **Traffic Analysis**: per‑IP counters, HTTP methods/statuses, top paths
- 🛡️ **CTI Enrichment**: VirusTotal + AbuseIPDB integration
- 👤 **Multi-user Support**: Per‑user API tokens and settings
- 🖱️ **Interactive UI**: Click any IP for detailed threat intelligence
- 📚 **History**: View old lookups and reuse cached results
- 📄 **Reports**: Export Markdown/HTML/TXT/PDF reports
- 🔒 **Secure**: API keys stored per-user in database
- 🎨 **Modern GUI**: Dark theme with intuitive interface

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


## 🚀 Installation & Quick Start

### Option A — Download EXE (Recommended) ✅
1. Go to [Releases](https://github.com/infat0x/l0g/releases)
2. Download `LogAnalysisCTI.exe`
3. Run the executable
4. Login with test credentials (below)
5. Configure API keys in Settings

### Option B — Run from Source
```bash
# Clone the repository
git clone https://github.com/infat0x/l0g.git
cd l0g

# Install dependencies
pip install -r scripts/packaging/requirements.txt

# Run GUI
python -m src.log_analysis_cti.gui_app

# Or run CLI
python -m src.log_analysis_cti.main <log_file_path>
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

## 🔑 API Configuration

### Method 1: In-App Settings (Recommended)
1. Run the application
2. Login with test credentials
3. Go to **Settings → API Keys**
4. Enter your API keys:
   - **VirusTotal API Key**: Get from [virustotal.com](https://www.virustotal.com/gui/my-apikey)
   - **AbuseIPDB API Key**: Get from [abuseipdb.com](https://www.abuseipdb.com/account/api)
   - **AI API Key**: Optional, for AI analysis features

### Method 2: Environment File
Create `.env` file in project root:
```dotenv
VIRUSTOTAL_API_KEY=your_virustotal_key_here
ABUSEIPDB_API_KEY=your_abuseipdb_key_here
AI_API_URL=https://api.mistral.ai/v1/chat/completions
AI_API_KEY=your_ai_api_key_here
```

> **Note**: Each user's API keys are stored securely in the database.

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔒 Security

- Keep `.env` private
- Do not share API tokens in screenshots
- Respect VirusTotal/AbuseIPDB usage policies
- Report security issues privately

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/infat0x/l0g/issues)
- **Discussions**: [GitHub Discussions](https://github.com/infat0x/l0g/discussions)

