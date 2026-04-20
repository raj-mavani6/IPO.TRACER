from flask import Flask, render_template, jsonify, request
from database import Database
import subprocess
import threading
import datetime
import re

app = Flask(__name__)
db = Database()

@app.route('/')
def index():
    ipos = db.get_all_ipos()
    # Pre-process for filtering
    for ipo in ipos:
        open_date = ipo.get('Summary Info', {}).get('Opening Date')
        parsed = parse_ipo_date(open_date)
        if parsed:
            ipo['filter_year'] = int(parsed.split('-')[0])
            ipo['filter_month'] = int(parsed.split('-')[1])
        else:
            ipo['filter_year'] = ipo.get('year', 'N/A')
            ipo['filter_month'] = 'N/A'
            
    return render_template('index.html', ipos=ipos)

@app.route('/ipo/<name>')
def ipo_detail(name):
    ipo = db.get_ipo_by_name(name)
    if ipo:
        return jsonify(ipo)
    return jsonify({"error": "IPO not found"}), 404

@app.route('/scrape', methods=['POST'])
def scrape():
    def run_scrape():
        subprocess.run(["python", "scraper.py"])
    
    thread = threading.Thread(target=run_scrape)
    thread.start()
    return jsonify({"status": "Live scraping started"})


def parse_ipo_date(date_str):
    if not date_str or date_str in ['N/A', '-', '', 'None']:
        return None
    
    # 1. Clean the string
    # Remove ordinal suffixes (st, nd, rd, th)
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str).strip()
    # Remove day names (Mon, Tuesday, etc)
    date_str = re.sub(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s*', '', date_str, flags=re.I)
    
    formats = [
        "%Y-%m-%d",    # 2024-12-23
        "%d %b %Y",    # 9 Apr 2026
        "%b %d, %Y",   # Dec 29, 2006
        "%d-%b-%Y",    # 09-Apr-2026
        "%Y/%m/%d"     # 2024/12/23
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
            
    print(f"⚠️ Could not parse date: {date_str}")
    return None

@app.route('/api/ipo_list')
def ipo_list():
    """Return data from the 'List' collection for the List View table."""
    premium_records = db.get_all_list_records()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    result = []
    for premium in premium_records:
        # Determine status based on dates if possible
        open_date = premium.get('open')
        close_date = premium.get('close')
        
        open_parsed = parse_ipo_date(open_date)
        close_parsed = parse_ipo_date(close_date)
        
        status = 'upcoming'
        # The Investorgain name often includes badges like 'O', 'C', 'U' 
        # but we can also compute it for consistency
        if open_parsed and close_parsed:
            if open_parsed <= today <= close_parsed: status = 'open'
            elif today > close_parsed: status = 'closed'
        
        # If the name has 'O', 'C', or 'U' at the end, respect that too
        name_raw = premium.get('name', 'Unknown')
        if name_raw.endswith(' O'): status = 'open'
        elif name_raw.endswith(' C'): status = 'closed'
        elif name_raw.endswith(' U'): status = 'upcoming'
        elif name_raw.endswith(' L'): status = 'closed' # Listed

        result.append({
            'name': name_raw,
            'gmp': premium.get('gmp', 'N/A'),
            'sub': premium.get('sub', 'N/A'),
            'price': premium.get('price', 'N/A'),
            'ipo_size': premium.get('ipo_size', 'N/A'),
            'lot': premium.get('lot', 'N/A'),
            'open': open_date or 'N/A',
            'close': close_date or 'N/A',
            'boa': premium.get('boa', 'N/A'),
            'dt': premium.get('dt', 'N/A'),
            'listing': premium.get('listing', 'N/A'),
            'updated_on': premium.get('timestamp', 'N/A'),
            'anchor': premium.get('anchor', 'N/A'),
            'status': status
        })
    
    return jsonify(result)

@app.route('/events')
def get_events():
    ipos = db.get_all_ipos()
    events = []
    
    for ipo in ipos:
        summary = ipo.get('Summary Info', {})
        name = ipo.get('ipo_name', 'Unknown IPO')
        
        # Opening Event
        open_date = parse_ipo_date(summary.get('Opening Date'))
        if open_date:
            events.append({
                'title': f'📈 Open: {name}',
                'start': open_date,
                'color': '#10b981',
                'extendedProps': {'ipo_name': name, 'type': 'open'}
            })
            
        # Closing Event
        close_date = parse_ipo_date(summary.get('Closing Date'))
        if close_date:
            events.append({
                'title': f'📉 Close: {name}',
                'start': close_date,
                'color': '#ef4444',
                'extendedProps': {'ipo_name': name, 'type': 'close'}
            })
        
        # BOA (Basis of Allotment) Event
        boa_date = parse_ipo_date(summary.get('Basis of Allotment'))
        if boa_date:
            events.append({
                'title': f'📋 BOA: {name}',
                'start': boa_date,
                'color': '#8b5cf6',
                'extendedProps': {'ipo_name': name, 'type': 'boa'}
            })

        # Listing Event
        listing_date = parse_ipo_date(summary.get('Listing Date'))
        if listing_date:
            events.append({
                'title': f'🔔 List: {name}',
                'start': listing_date,
                'color': '#3b82f6',
                'extendedProps': {'ipo_name': name, 'type': 'listing'}
            })
            
    return jsonify(events)

@app.route('/api/calendar_timeline')
def calendar_timeline():
    """Return date-wise IPO events for the Timeline Calendar View."""
    ipos = db.get_all_ipos()
    
    # Build a date → { open: [], close: [], boa: [], unblock: [], listing: [] } map
    date_map = {}
    
    for ipo in ipos:
        summary = ipo.get('Summary Info', {})
        name = ipo.get('ipo_name', 'Unknown IPO')
        
        date_fields = {
            'open': parse_ipo_date(summary.get('Opening Date')),
            'close': parse_ipo_date(summary.get('Closing Date')),
            'boa': parse_ipo_date(summary.get('Basis of Allotment')),
            'unblock': parse_ipo_date(summary.get('Initiation of Refunds')),
            'listing': parse_ipo_date(summary.get('Listing Date'))
        }
        
        for category, date_val in date_fields.items():
            if date_val:
                if date_val not in date_map:
                    date_map[date_val] = {'date': date_val, 'open': [], 'close': [], 'boa': [], 'unblock': [], 'listing': []}
                date_map[date_val][category].append(name)
    
    # Sort by date descending (newest first)
    result = sorted(date_map.values(), key=lambda x: x['date'], reverse=True)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
