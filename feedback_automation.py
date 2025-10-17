from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from random import randint
import time


def create_driver():
    """
    Sets up and returns an optimized Selenium WebDriver for Chrome.
    """
    options = webdriver.ChromeOptions()
    
    # Basic headless options
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Memory optimization flags
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    options.add_argument("--memory-pressure-off")
    
    # Smaller window size
    options.add_argument("--window-size=1280,720")
    
    # Disable images to save memory (if not needed)
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "disk-cache-size": 4096,
        "media-cache-size": 0
    }
    options.add_experimental_option("prefs", prefs)
    
    # Memory limit
    options.add_argument("--max_old_space_size=256")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    
    return driver


def run_feedback_automation(index, rollno, password, status_queue=None):
    """
    Main automation function. Modified to work with RQ.
    Returns result dict instead of using status_queue.
    """
    browser = None
    try:
        browser = create_driver()
        wait = WebDriverWait(browser, 20)

        # Login
        browser.get("https://ecampus.psgtech.ac.in/studzone")
        
        rollno_field = wait.until(EC.presence_of_element_located((By.ID, "rollno")))
        rollno_field.send_keys(rollno)
        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(password)
        checkbox = browser.find_element(By.ID, "terms")
        browser.execute_script("arguments[0].click();", checkbox)
        login_button = browser.find_element(By.ID, "btnLogin")
        browser.execute_script("arguments[0].click();", login_button)
        
        # Navigate to feedback
        feedback_card = wait.until(EC.element_to_be_clickable((By.XPATH, "//h5[text()='Feedback']")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", feedback_card)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
        feedbacks = browser.find_elements(By.CLASS_NAME, "card-body")
        browser.execute_script("arguments[0].click();", feedbacks[index])
        
        # Process form based on type
        if index == 0:
            endsem_form(browser)
        else:
            intermediate_form(browser)
        
        return {"success": True, "message": "Feedback submitted successfully"}

    except TimeoutException as e:
        if browser:
            browser.save_screenshot("/tmp/debug_screenshot.png")
        raise Exception(f"Timeout: {str(e)}. Check credentials or website status.")
    
    except Exception as e:
        raise Exception(f"Automation failed: {str(e)}")
    
    finally:
        if browser:
            # Clean up
            browser.delete_all_cookies()
            browser.execute_script("window.localStorage.clear();")
            browser.execute_script("window.sessionStorage.clear();")
            browser.quit()


def intermediate_form(browser):
    wait = WebDriverWait(browser, 15)
    courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
    
    if not courses:
        raise Exception("No intermediate feedback courses found.")

    num_courses = len(courses)
    for i in range(num_courses):
        courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", courses[i])
        
        questions_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.bottom-0"))).text
        questions = int(questions_text.split()[-1])
        clicks = 0
        
        while clicks < questions:
            try:
                radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[@for='radio-{clicks + 1}-1']")))
                browser.execute_script("arguments[0].click();", radio_button)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='carousel-control-next']")))
                browser.execute_script("arguments[0].click();", next_button)
                clicks += 1
                time.sleep(0.3)
            except StaleElementReferenceException:
                continue
        
        back_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "overlay")))
        browser.execute_script("arguments[0].click();", back_button)
        time.sleep(0.5)


def endsem_form(browser):
    wait = WebDriverWait(browser, 15)
    staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
    
    if not staff_list:
        raise Exception("Could not find staff list for feedback.")

    num_staff = len(staff_list)
    for i in range(num_staff):
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", staff_list[i])
        
        wait.until(EC.presence_of_element_located((By.ID, "feedbackTableBody")))
        review_list = browser.find_elements(By.CSS_SELECTOR, "td.question-cell")
        
        for count in range(1, len(review_list) + 1):
            star_button = browser.find_element(
                By.XPATH, 
                f"//tbody[@id='feedbackTableBody']/tr[{count}]/td[@class='rating-cell']/div[@class='star-rating']/label[{randint(4, 5)}]"
            )
            browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", star_button)
        
        submit_button = browser.find_element(By.ID, "btnSave")
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", submit_button)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img.img-fluid")))
        time.sleep(1)

    final_submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnFinalSubmit")))
    browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", final_submit_button)
