import time
import re
import json
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
    
    # Extract headers
    header_row = rows[0]
    headers = [clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
    
    if not headers: return data

    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) == len(headers):
            row_data = {headers[i]: clean_text(cols[i].get_text()) for i in range(len(headers))}
            data.append(row_data)
        elif len(cols) == 2: # Key-Value pair table
            key = clean_text(cols[0].get_text())
            val = clean_text(cols[1].get_text())
            data.append({"Key": key, "Value": val})
    return data

def extract_table(soup, title_keywords):
    """
    Finds a table based on its preceding heading or content keywords.
    """
    all_tables = soup.find_all('table')
    for table in all_tables:
        table_text = table.get_text().lower()
        if all(k.lower() in table_text for k in title_keywords):
            return parse_html_table(table)
            
    headings = soup.find_all(['h2', 'h3', 'h4', 'div', 'strong', 'p', 'span'])
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
    # Wait for tables to load
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    except:
        pass
    time.sleep(2) # Extra buffer
    return BeautifulSoup(driver.page_source, 'html.parser')

def scrape_ipo_details_page(driver, url):
    soup = get_page_soup(driver, url)
    data = {}
    
    summary_data = {}
    # Method 1: Search for specific labels in headings/divs
    targets = {
        "Opening Date": ["Issue Opening Date"],
        "Closing Date": ["Issue Closing Date"],
        "Price Band": ["Price Band"],
        "Listing Date": ["Listing Date"]
    }
    
    for label, keywords in targets.items():
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'strong', 'p']:
            elements = soup.find_all(tag)
            for el in elements:
                el_text = el.get_text().lower()
                if all(k.lower() in el_text for k in keywords):
                    # If the element text is just the label, the value is probably in the next sibling
                    clean_el_text = clean_text(el.get_text())
                    if len(clean_el_text) < 30:
                        nxt = el.find_next()
                        if nxt:
                            val = clean_text(nxt.get_text())
                            if val: summary_data[label] = val
                            break
                    else:
                        summary_data[label] = clean_el_text.split(':')[-1].strip()
                        break
            if label in summary_data: break

    # Method 2: Table Fallback
    if len(summary_data) < 4:
        summary_table = soup.find('table', class_='table-striped')
        if not summary_table:
            all_tables = soup.find_all('table')
            if all_tables: summary_table = all_tables[0]

        if summary_table:
            for row in summary_table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    key = clean_text(cols[0].get_text()).lower()
                    val = clean_text(cols[1].get_text())
                    if "opening date" in key: summary_data['Opening Date'] = val
                    elif "closing date" in key: summary_data['Closing Date'] = val
                    elif "price band" in key: summary_data['Price Band'] = val
                    elif "listing date" in key: summary_data['Listing Date'] = val
    
    data['Summary Info'] = summary_data
    data['IPO Details'] = extract_table(soup, ['IPO', 'Details'])
    data['IPO Important Dates'] = extract_table(soup, ['Important', 'Dates'])
    data['IPO GMP'] = extract_table(soup, ['IPO', 'GMP'])
    data['Issue Reservation'] = extract_table(soup, ['Issue', 'Reservation'])
    data['IPO Lot Size'] = extract_table(soup, ['Lot', 'Size'])
    data['IPO Day-wise Subscription Status'] = extract_table(soup, ['Subscription', 'Status'])
    data['Company Financials'] = extract_table(soup, ['Financials'])
    data['IPO Objective'] = extract_table(soup, ['Objective'])
    data['KPI'] = extract_table(soup, ['Key', 'Performance', 'Indicator'])
    data['IPO Peer Comparison'] = extract_table(soup, ['Peer', 'Comparison'])
    data['IPO Lead Manager'] = extract_table(soup, ['Lead', 'Manager'])
    
    return data

def scrape_recommendations_page(driver, url):
    soup = get_page_soup(driver, url)
    return {"IPO Recommendations": extract_table(soup, ['Recommendations'])}

def scrape_subscription_page(driver, url):
    soup = get_page_soup(driver, url)
    data = {}
    data['IPO Live Subscription'] = extract_table(soup, ['Live', 'Subscription'])
    data['Current Subscription Data'] = extract_table(soup, ['Current', 'Subscription'])
    data['Anchor Investor Allocation'] = extract_table(soup, ['Anchor', 'Investor'])
    return data

def scrape_gmp_page(driver, url):
    soup = get_page_soup(driver, url)
    return {"IPO Day-wise GMP Trend": extract_table(soup, ['GMP', 'Trend'])}

def get_ipo_list(driver):
    url = "https://www.investorgain.com/report/watch-live-ipo-event-calendar/554/"
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    ipo_links = []
    links = soup.find_all('a', href=re.compile(r'/ipo/.*?/\d+/'))
    for link in links:
        href = link.get('href')
        name = clean_text(link.get_text())
        if name and href and len(name) > 3:
            full_url = urljoin("https://www.investorgain.com", href)
            ipo_links.append({"name": name, "url": full_url})
    
    unique_links = {}
    for item in ipo_links:
        unique_links[item['url']] = item['name']
        
    return unique_links

def scrape_investorgain_list(driver):
    url = "https://www.investorgain.com/report/live-ipo-gmp/331/"
    driver.get(url)
    
    # Scroll down to trigger any lazy-loaded content
    driver.execute_script("window.scrollTo(0, 1000);")
    time.sleep(5)
    
    # Wait for the table to have at least one non-empty data row
    try:
        WebDriverWait(driver, 20).until(
            lambda d: len(d.execute_script("return Array.from(document.querySelectorAll('#report_table tbody tr')).filter(r => r.innerText.trim().length > 0)")) > 0
        )
        print("Table data detected in DOM.")
    except Exception as e:
        print(f"Warning: Table data not detected within timeout: {e}")

    # Use JavaScript to extract data directly to bypass any Soup parsing issues with empty rows
    js_extract = """
    let rows = Array.from(document.querySelectorAll('#report_table tbody tr'));
    return rows.map(r => {
        let cells = Array.from(r.querySelectorAll('td'));
        if (cells.length < 13) return null;
        
        // Helper to get text or symbol
        function get_cell(index) {
            let cell = cells[index-1];
            if (!cell) return "";
            if (index === 13) {
                return (cell.querySelector('.fa-check') || cell.innerText.includes('✅')) ? "✅" : "❌";
            }
            return cell.innerText.trim();
        }

        return {
            name: get_cell(1),
            gmp: get_cell(2),
            sub: get_cell(4),
            price: get_cell(5),
            ipo_size: get_cell(6),
            lot: get_cell(7),
            open: get_cell(8),
            close: get_cell(9),
            boa: get_cell(10),
            dt: get_cell(10),
            listing: get_cell(11),
            updated_on: get_cell(12),
            anchor: get_cell(13)
        };
    }).filter(x => x !== null);
    """
    
    extracted_data = driver.execute_script(js_extract)
    
    records = []
    count = 0
    for item in extracted_data:
        if count >= 30:
            break
        if item['name']:
            item['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
            records.append(item)
            count += 1
            
    return records

def run_detail_scraper():
    print("Starting Detailed IPO Scraper...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Fetching IPO list from calendar...")
        ipo_map = get_ipo_list(driver)
        print(f"Found {len(ipo_map)} IPOs for details.")
        
        for ipo_url, ipo_name in ipo_map.items():
            print(f"--- Scraping Details: {ipo_name} ---")
            try:
                base_url = ipo_url
                recommend_url = ipo_url.replace("/ipo/", "/recommendations/")
                subscribe_url = ipo_url.replace("/ipo/", "/subscription/")
                gmp_url = ipo_url.replace("/ipo/", "/gmp/")
                
                all_data = {"ipo_name": ipo_name, "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")}
                all_data.update(scrape_ipo_details_page(driver, base_url))
                all_data.update(scrape_recommendations_page(driver, recommend_url))
                all_data.update(scrape_subscription_page(driver, subscribe_url))
                all_data.update(scrape_gmp_page(driver, gmp_url))
                
                db.upsert_ipo(ipo_name, all_data)
                
            except Exception as e:
                print(f"Error scraping data for {ipo_name}: {e}")
    finally:
        driver.quit()
        print("Detailed Scraper Finished.")

def run_list_scraper():
    print("Starting Investorgain List Scraper...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        records = scrape_investorgain_list(driver)
        print(f"Scraped {len(records)} records for List view.")
        for rec in records:
            db.upsert_list_record(rec['name'], rec)
    finally:
        driver.quit()
        print("List Scraper Finished.")

def run_scraper():
    import threading
    
    print("Initializing simultaneous scrapers...")
    t1 = threading.Thread(target=run_detail_scraper)
    t2 = threading.Thread(target=run_list_scraper)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    print("All scraping tasks completed.")

if __name__ == "__main__":
    run_scraper()