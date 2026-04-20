import time
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from database import Database

db = Database()

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())

def parse_html_table(table):
    data = []
    rows = table.find_all('tr')
    if not rows:
        return data
    
    header_row = rows[0]
    headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
    
    if not headers: return data

    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) == len(headers):
            row_data = {headers[i]: clean_text(cols[i].get_text()) for i in range(len(headers))}
            data.append(row_data)
        elif len(cols) == 2:
            key = clean_text(cols[0].get_text())
            val = clean_text(cols[1].get_text())
            data.append({"Key": key, "Value": val})
    return data

def extract_table(soup, title_keywords):
    """Finds a table based on its content or preceding heading keywords."""
    # Method 1: Search within table content
    all_tables = soup.find_all('table')
    for table in all_tables:
        table_text = table.get_text().lower()
        if all(k.lower() in table_text for k in title_keywords):
            return parse_html_table(table)
    
    # Method 2: Search via preceding headings
    headings = soup.find_all(['h2', 'h3', 'h4', 'div', 'strong', 'p', 'span', 'li'])
    for h in headings:
        text = h.get_text().lower()
        if all(k.lower() in text for k in title_keywords):
            curr = h
            for _ in range(8):
                curr = curr.find_next()
                if not curr: break
                if curr.name == 'table':
                    return parse_html_table(curr)
    return []

def get_page_soup(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    except:
        pass
    time.sleep(1.5)
    return BeautifulSoup(driver.page_source, 'html.parser')

def parse_ipo_date(date_str):
    if not date_str or date_str in ['N/A', '[.]', '', '-', 'Not Available']:
        return None
    
    clean_date = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*', '', date_str, flags=re.I)
    clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', clean_date)
    clean_date = clean_text(clean_date)
    
    formats = ["%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(clean_date, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
            
    if '-' in clean_date:
        parts = clean_date.split('-')
        return parse_ipo_date(parts[0].strip())
        
    return None

# =============================================
# CHITTORGARH DETAIL PAGE SCRAPING
# =============================================

def scrape_ipo_details_page(driver, url):
    """
    Scrape all required data from a Chittorgarh IPO detail page:
    - Summary Info (Opening Date, Closing Date, Price Band, Listing Date)
    - IPO Details table
    - IPO Timetable table
    - IPO Lot Size table
    - IPO Anchor Investors table
    - Issue Reservation table
    - Company Financials table
    - IPO Objects of the Issue table
    - Key Performance Indicator table
    - IPO Subscription Status table
    - IPO Registrar table
    - IPO Lead Manager(s) table
    """
    soup = get_page_soup(driver, url)
    data = {}
    
    # --- Summary Info ---
    summary_data = {}
    targets = {
        "Opening Date": ["IPO Open", "Opening Date"],
        "Closing Date": ["IPO Close", "Closing Date"],
        "Price Band": ["Price Band", "Issue Price", "Fixed Price"],
        "Listing Date": ["Listing Date", "Listing Day"]
    }
    
    for label, keywords in targets.items():
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'strong', 'p', 'span', 'li']:
            elements = soup.find_all(tag)
            for el in elements:
                el_text = el.get_text()
                if any(k.lower() == clean_text(el_text).lower() for k in keywords):
                    nxt = el.find_next()
                    if nxt:
                        val = clean_text(nxt.get_text())
                        if val and len(val) < 50:
                            summary_data[label] = parse_ipo_date(val) if "Date" in label else val
                            break
            if label in summary_data: break

    # Fallback: Table Search for summary fields
    if len(summary_data) < 2:
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) == 2:
                    k = clean_text(cols[0].get_text()).lower()
                    v = clean_text(cols[1].get_text())
                    if "open" in k and "date" in k: summary_data["Opening Date"] = parse_ipo_date(v)
                    elif "close" in k and "date" in k: summary_data["Closing Date"] = parse_ipo_date(v)
                    elif "price" in k: summary_data["Price Band"] = v
                    elif "listing" in k and "date" in k: summary_data["Listing Date"] = parse_ipo_date(v)

    data['Summary Info'] = summary_data
    
    # --- All Required Tables from Chittorgarh ---
    data['IPO Details'] = extract_table(soup, ['IPO', 'Details'])
    data['IPO Timetable'] = extract_table(soup, ['Timetable'])
    data['IPO Lot Size'] = extract_table(soup, ['Lot', 'Size'])
    data['IPO Anchor Investors'] = extract_table(soup, ['Anchor', 'Investor'])
    data['Issue Reservation'] = extract_table(soup, ['Issue', 'Reservation'])
    data['Company Financials'] = extract_table(soup, ['Financials'])
    data['IPO Objective'] = extract_table(soup, ['Objective'])
    data['KPI'] = extract_table(soup, ['Key', 'Performance', 'Indicator'])
    data['IPO Subscription Status'] = extract_table(soup, ['Subscription', 'Status'])
    data['IPO Registrar'] = extract_table(soup, ['Registrar'])
    data['IPO Lead Manager'] = extract_table(soup, ['Lead', 'Manager'])
    
    return data

# =============================================
# INVESTORGAIN URL DISCOVERY (Pre-built Mapping)
# =============================================

def normalize_for_match(name):
    """Normalize an IPO name for fuzzy matching."""
    n = name.lower()
    # Remove common suffixes
    n = re.sub(r'\b(limited|ltd|ipo|bse|sme|nse|inv[ai]t)\b', '', n)
    n = re.sub(r'\(.*?\)', '', n)
    n = n.replace('.', '').replace(',', '').replace('-', ' ')
    return ' '.join(n.split())

def build_investorgain_map(driver):
    """
    Pre-build a comprehensive mapping of IPO names to Investorgain GMP URLs
    by scraping their IPO Performance History pages (300+ records per year).
    
    Returns dict: { normalized_name: gmp_url }
    """
    ig_map = {}
    
    # Scrape performance history for recent years (2020-2026)
    years_to_scrape = list(range(2026, 2005, -1))
    
    for year in years_to_scrape:
        perf_url = f"https://www.investorgain.com/report/ipo-performance-history/486/all/?year={year}"
        print(f"  📊 Loading Investorgain map for {year}...")
        
        try:
            driver.get(perf_url)
            time.sleep(3)
            
            # Use JavaScript to extract all IPO links from the report table
            js_extract = """
            let links = document.querySelectorAll('table a[href*="/ipo/"], table a[href*="/gmp/"]');
            let result = [];
            links.forEach(a => {
                let name = a.innerText.trim();
                let href = a.getAttribute('href');
                if (name && href && name.length > 2) {
                    result.push({ name: name, href: href });
                }
            });
            return result;
            """
            link_data = driver.execute_script(js_extract)
            
            count = 0
            for item in link_data:
                name = item['name']
                href = item['href']
                full_url = urljoin("https://www.investorgain.com", href)
                
                # Normalize to /gmp/ URL
                if '/ipo/' in full_url:
                    full_url = full_url.replace('/ipo/', '/gmp/')
                
                norm = normalize_for_match(name)
                if norm and norm not in ig_map:
                    ig_map[norm] = full_url
                    count += 1
            
            print(f"    ✅ Added {count} new IPOs from {year} (Total: {len(ig_map)})")
            
        except Exception as e:
            print(f"    ⚠️ Failed to load {year}: {e}")
    
    # Also scrape the live GMP report for the newest IPOs
    try:
        print(f"  📊 Loading Investorgain live GMP report...")
        driver.get("https://www.investorgain.com/report/live-ipo-gmp/331/")
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(4)
        
        js_extract_live = """
        let links = document.querySelectorAll('#report_table a[href*="/ipo/"], #report_table a[href*="/gmp/"]');
        let result = [];
        links.forEach(a => {
            let name = a.innerText.trim();
            let href = a.getAttribute('href');
            if (name && href && name.length > 2) {
                result.push({ name: name, href: href });
            }
        });
        return result;
        """
        live_data = driver.execute_script(js_extract_live)
        count = 0
        for item in live_data:
            full_url = urljoin("https://www.investorgain.com", item['href'])
            if '/ipo/' in full_url:
                full_url = full_url.replace('/ipo/', '/gmp/')
            norm = normalize_for_match(item['name'])
            if norm and norm not in ig_map:
                ig_map[norm] = full_url
                count += 1
        print(f"    ✅ Added {count} new IPOs from live report (Total: {len(ig_map)})")
    except Exception as e:
        print(f"    ⚠️ Failed to load live report: {e}")
    
    return ig_map

def find_investorgain_url(ig_map, ipo_name):
    """
    Look up the Investorgain GMP URL for an IPO from the pre-built map.
    Uses normalized name matching with fallback to partial overlap.
    """
    norm = normalize_for_match(ipo_name)
    
    # 1. Direct match
    if norm in ig_map:
        return ig_map[norm]
    
    # 2. Fuzzy match — find best overlap
    name_words = set(norm.split())
    best_url = None
    best_score = 0
    
    for map_name, url in ig_map.items():
        map_words = set(map_name.split())
        overlap = name_words & map_words
        score = len(overlap)
        
        if score > best_score and score >= min(2, len(name_words)):
            best_score = score
            best_url = url
    
    return best_url

# =============================================
# INVESTORGAIN PAGE SCRAPERS
# =============================================

def scrape_investorgain_gmp(driver, gmp_url):
    """
    From the Investorgain GMP page, scrape:
    - IPO Day-wise Subscription Status table
    - IPO Day-wise GMP Trend table
    """
    data = {}
    try:
        soup = get_page_soup(driver, gmp_url)
        data['IPO Day-wise Subscription Status'] = extract_table(soup, ['Subscription'])
        data['IPO Day-wise GMP Trend'] = extract_table(soup, ['GMP'])
    except Exception as e:
        print(f"        GMP page error: {e}")
    return data

def scrape_investorgain_recommendations(driver, gmp_url):
    """
    From the Investorgain recommendations page, scrape:
    - IPO Recommendations table
    """
    data = {}
    try:
        rec_url = gmp_url.replace('/gmp/', '/recommendations/')
        soup = get_page_soup(driver, rec_url)
        data['IPO Recommendations'] = extract_table(soup, ['Recommendation'])
    except Exception as e:
        print(f"        Recommendations page error: {e}")
    return data

def scrape_investorgain_subscription(driver, gmp_url):
    """
    From the Investorgain subscription page, scrape:
    - IPO Live Subscription table
    - Current Subscription Data table
    - Anchor Investor Allocation table
    """
    data = {}
    try:
        sub_url = gmp_url.replace('/gmp/', '/subscription/')
        soup = get_page_soup(driver, sub_url)
        data['IPO Live Subscription'] = extract_table(soup, ['Live', 'Subscription'])
        data['Current Subscription Data'] = extract_table(soup, ['Current', 'Subscription'])
        data['Anchor Investor Allocation'] = extract_table(soup, ['Anchor', 'Investor'])
    except Exception as e:
        print(f"        Subscription page error: {e}")
    return data

# =============================================
# DRIVER & MAIN ENTRY POINT
# =============================================

def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def run_historical_scraper():
    print("🚀 Initializing Historical Scraper (Cloud API 2006-2026)...")
    driver = create_driver()
    
    try:
        # ── Step 0: Pre-build Investorgain URL Map ──
        print("\n📊 Phase 1: Building Investorgain URL Mapping...")
        ig_map = build_investorgain_map(driver)
        print(f"✅ Investorgain map built with {len(ig_map)} IPOs.\n")
        
        # ── Step 1: Loop through Chittorgarh years ──
        for year in range(2026, 2005, -1):
            print(f"\n📅 Syncing Year: {year}")
            
            page = 1
            while True:
                # pageSizeCode 5 = 100 records per page
                api_url = f"https://webnodejs.chittorgarh.com/cloud/report/data-read/82/{page}/5/{year}/2026-27/0/all/0?search=&v=10-16"
                print(f"  🔗 Fetching API Page {page}...")
                
                try:
                    response = requests.get(api_url, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    print(f"    ❌ API Error on page {page}: {e}")
                    break
                
                rows = data.get("reportTableData", [])
                total_pages = data.get("totalPages", 1)
                
                if not rows:
                    print(f"    No more records for {year}.")
                    break

                print(f"    Found {len(rows)} records. Processing...")
                for row in rows:
                    # Column 'Company' contains the HTML link
                    company_html = row.get("Company", "")
                    soup = BeautifulSoup(company_html, 'html.parser')
                    link_tag = soup.find('a')
                    
                    if link_tag:
                        name = clean_text(link_tag.get_text())
                        url = urljoin("https://www.chittorgarh.com", link_tag.get('href'))
                        
                        print(f"      📄 Scraping: {name}")
                        try:
                            all_data = {
                                "ipo_name": name, 
                                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                "source": "Chittorgarh",
                                "year": year
                            }
                            
                            # ── Scrape Chittorgarh Detail Page ──
                            try:
                                details = scrape_ipo_details_page(driver, url)
                            except Exception as crash_e:
                                if "Connection" in str(crash_e) or "session" in str(crash_e).lower():
                                    print("        ⚠️ Driver session lost. Restarting browser...")
                                    try: driver.quit()
                                    except: pass
                                    driver = create_driver()
                                    details = scrape_ipo_details_page(driver, url)
                                else:
                                    raise crash_e
                                    
                            all_data.update(details)
                            
                            # ── Lookup & Scrape Investorgain Pages ──
                            ig_gmp_url = find_investorgain_url(ig_map, name)
                            
                            if ig_gmp_url:
                                print(f"        ✅ Investorgain match: {ig_gmp_url}")
                                
                                # GMP page → Day-wise Subscription Status + GMP Trend
                                gmp_data = scrape_investorgain_gmp(driver, ig_gmp_url)
                                all_data.update(gmp_data)
                                
                                # Recommendations page → IPO Recommendations
                                rec_data = scrape_investorgain_recommendations(driver, ig_gmp_url)
                                all_data.update(rec_data)
                                
                                # Subscription page → Live Sub + Current Sub + Anchor Allocation
                                sub_data = scrape_investorgain_subscription(driver, ig_gmp_url)
                                all_data.update(sub_data)
                            else:
                                print(f"        ⚠️ No Investorgain match found.")
                                
                            db.upsert_ipo(name, all_data)
                        except Exception as e:
                            print(f"        ❌ Error: {e}")
                    
                if page >= total_pages:
                    break
                page += 1
                
            # Periodically restart driver to keep memory low
            if year % 2 == 0:
                print("  ♻️ Recycling browser session...")
                try: driver.quit()
                except: pass
                driver = create_driver()

    finally:
        if driver:
            try: driver.quit()
            except: pass
        print("\n✅ Historical Data Sync Completed Successfully.")

if __name__ == "__main__":
    run_historical_scraper()
