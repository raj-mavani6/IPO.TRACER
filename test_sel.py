from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

def test():
    print("Starting regular selenium...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.investorgain.com/report/watch-live-ipo-event-calendar/554/")
    print(len(driver.page_source))
    driver.quit()
    print("Success")

if __name__ == "__main__":
    test()
