# IPO.TRACER: Advanced IPO Event Calendar & Analytics Dashboard

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13-black.svg)
![Flask](https://img.shields.io/badge/framework-Flask-red.svg)
![MongoDB](https://img.shields.io/badge/database-MongoDB-green.svg)

**IPO.TRACER** is a premium, real-time analytics dashboard designed to track Indian Initial Public Offerings (IPOs). It combines high-performance web scraping with an AI-driven data extraction engine to provide investors with deep insights into market sentiment, financials, and event timelines.

---

## 🌟 Key Features

### 1. Hybrid Multi-View Interface
*   **Premium Grid View**: Modern glassmorphism cards with dynamic hover states.
*   **Pro List View**: A high-density, searchable data table with real-time status badges (Open, Closed, Upcoming).
*   **Interactive Calendar**: 
    *   **Monthly View**: Classic monthly grid for quick date tracking.
    *   **Timeline View**: A chronological audit of Open, Close, Allotment (BOA), and Listing events.

### 2. Intelligent Scraper Bridge
*   Multi-source support (Chittorgarh, Investorgain).
*   Semantic data mapping to handle inconsistent reporting formats.
*   Numeric Purification logic to distinguish between percentages and absolute currency metrics.

### 3. Comprehensive Analytics
*   **Market Sentiment**: Tracks GMP (Grey Market Premium) and Estimated Profits.
*   **Investor Interest**: Real-time subscription data for QIB, NII, and Retail investors.
*   **Deep Financials**: Automated extraction of PAT, Revenue, and Net Worth trends.

---

## 🚀 Tech Stack

*   **Backend**: Python (Flask), MongoDB.
*   **Frontend**: HTML5, Tailwind CSS, JavaScript (jQuery).
*   **Animations**: GSAP (GreenSock Animation Platform).
*   **Data Visuals**: Chart.js, FullCalendar 6.
*   **Scraping**: BeautifulSoup4, Subprocess Bridge.

---

## ⚙️ Installation & Setup

### Prerequisites
*   Python 3.10+
*   MongoDB (Local or Atlas)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/ipo-tracer.git
cd ipo-tracer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Database
Ensure your MongoDB service is running. By default, the app looks for a local instance. You can modify the connection string in `database.py`.

### 4. Run the Application
```bash
python app.py
```
Open `http://127.0.0.1:5000` in your browser.

---

## 🛠️ High-Resilience Extraction Strategy

Unlike traditional scrapers that rely on fragile CSS selectors, **IPO.TRACER** implements a **Semantic Keyword Extraction Engine**. This allows the system to remain stable even when data sources change their HTML structure:

*   **Vertical vs. Horizontal Detection**: Intelligent logic that determines if a table is transposed (headers on the left) or standard (headers on top).
*   **Fuzzy Priority Search**: Implements a tiered search (Tier 1: Direct Match, Tier 2: Bucket Search, Tier 3: Global Fuzzy Search) to locate elusive financial metrics like PAT and Net Worth.
*   **Numeric Purification**: A custom validation layer that strips non-numeric symbols and intelligently rejects percentage figures when an absolute currency value is required.

---

## 🔌 Internal Dashboard API

The backend serves a high-speed JSON API for all frontend components:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/ipo_list` | GET | Returns a consolidated list of all IPOs with status markers (O/C/U). |
| `/events` | GET | Serves date-wise events formatted specifically for FullCalendar orchestration. |
| `/api/calendar_timeline` | GET | Returns a chronological data map for the Timeline View. |
| `/ipo/<name>` | GET | Fetches the full historical and financial dataset for a specific IPO. |
| `/scrape` | POST | Triggers a non-blocking background sync process. |

---

## 🏗️ System Architecture Flow

1.  **The Producer (Scraper Bridge)**: Flask initiates an asynchronous subprocess using `subprocess.run`, allowing users to continue browsing while the sync runs in the background.
2.  **The Brain (Extraction Logic)**: Raw HTML is converted into a semantic dictionary, standardizing diverse data points from Mainboard and SME filings.
3.  **The Consumer (Frontend)**: A sophisticated jQuery wrapper handles data fetching and populates the hybrid view system.
4.  **Motion Design**: Handled by **GSAP**, which choreographs entry animations for every card and list row to reduce perceived latency.

---

## ⚡ Performance & Security

*   **MongoDB Indexing**: Key-value indexing on `ipo_name` and `Opening Date` allows for sub-100ms queries across thousands of records.
*   **Request Throttling**: The scraper implements intelligent delay patterns and User-Agent rotation to prevent IP blocking from source websites.
*   **Isolated Failure Zones**: Each section of the frontend is wrapped in an independent `try-catch` block. If a specific source fails to provide one data point, the rest of the dashboard remains fully functional.

---

## 🤖 Built with Advanced AI

This project was developed through a high-level collaboration between human engineering and State-of-the-Art (SOTA) AI coding agents:

*   **Claude Code** (Claude 3.5 Sonnet): Orchestrated the project architecture and implemented complex data-parsing logic.
*   **Open Codex** (GPT-4o): Fine-tuned the regex algorithms for date standardization and financial keyword mapping.

---


## 📈 Project Roadmap
- [ ] AI Sentiment Analysis for IPO News.
- [ ] User Portfolio Tracking & Allotment Calculator.
- [ ] Email/Telegram Push Notifications for Subscription alerts.
- [ ] Dark Mode / Light Mode toggle.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements.

---

*Built with ❤️ for the Indian Investment Community.*
