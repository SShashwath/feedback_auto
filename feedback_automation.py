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
    
    # Disable images to save memory
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
        print(f"Starting automation for rollno: {rollno}, feedback type: {index}")
        browser = create_driver()
        wait = WebDriverWait(browser, 20)

        # Login
        print("Accessing login page...")
        browser.get("https://ecampus.psgtech.ac.in/studzone")
        
        rollno_field = wait.until(EC.presence_of_element_located((By.ID, "rollno")))
        rollno_field.send_keys(rollno)
        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(password)
        checkbox = browser.find_element(By.ID, "terms")
        browser.execute_script("arguments[0].click();", checkbox)
        login_button = browser.find_element(By.ID, "btnLogin")
        browser.execute_script("arguments[0].click();", login_button)
        print("Login submitted")
        
        # Navigate to feedback
        print("Navigating to feedback section...")
        feedback_card = wait.until(EC.element_to_be_clickable((By.XPATH, "//h5[text()='Feedback']")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", feedback_card)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
        feedbacks = browser.find_elements(By.CLASS_NAME, "card-body")
        browser.execute_script("arguments[0].click();", feedbacks[index])
        print(f"Selected feedback type: {'End-Sem' if index == 0 else 'Intermediate'}")
        
        # Process form based on type
        if index == 0:
            endsem_form(browser)
        else:
            intermediate_form(browser)
        
        print("Automation completed successfully!")
        return {"success": True, "message": "Feedback submitted successfully"}

    except TimeoutException as e:
        error_msg = f"Timeout: {str(e)}. Check credentials or website status."
        print(f"ERROR: {error_msg}")
        if browser:
            browser.save_screenshot("/tmp/debug_screenshot.png")
        raise Exception(error_msg)
    
    except Exception as e:
        error_msg = f"Automation failed: {str(e)}"
        print(f"ERROR: {error_msg}")
        raise Exception(error_msg)
    
    finally:
        if browser:
            print("Cleaning up browser...")
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
    print(f"Found {num_courses} courses for intermediate feedback")
    
    for i in range(num_courses):
        courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", courses[i])
        print(f"Processing course {i+1}/{num_courses}")
        
        questions_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.bottom-0"))).text
        questions = int(questions_text.split()[-1])
        print(f"  Found {questions} questions")
        clicks = 0
        
        while clicks < questions:
            try:
                radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[@for='radio-{clicks + 1}-1']")))
                browser.execute_script("arguments[0].click();", radio_button)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='carousel-control-next']")))
                browser.execute_script("arguments[0].click();", next_button)
                clicks += 1
                print(f"  Answered question {clicks}/{questions}")
                time.sleep(0.3)
            except StaleElementReferenceException:
                continue
        
        back_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "overlay")))
        browser.execute_script("arguments[0].click();", back_button)
        print(f"Completed course {i+1}/{num_courses}")
        time.sleep(0.5)


def endsem_form(browser):
    wait = WebDriverWait(browser, 20)
    
    try:
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
    except TimeoutException:
        raise Exception("Could not find staff list for feedback.")
    
    if not staff_list:
        raise Exception("No staff members found in feedback form.")

    num_staff = len(staff_list)
    print(f"Found {num_staff} staff members to process")
    
    for i in range(num_staff):
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
        browser.execute_script("arguments[0].scrollIntoView(true);", staff_list[i])
        time.sleep(0.5)
        browser.execute_script("arguments[0].click();", staff_list[i])
        
        try:
            wait.until(EC.presence_of_element_located((By.ID, "feedbackTableBody")))
            time.sleep(1)
        except TimeoutException:
            print(f"Warning: Feedback table not found for staff {i+1}, skipping...")
            continue
        
        review_rows = browser.find_elements(By.CSS_SELECTOR, "tbody#feedbackTableBody tr")
        print(f"Processing {len(review_rows)} questions for staff {i+1}")
        
        if len(review_rows) == 0:
            print("No questions found, moving to next staff member...")
            continue
        
        for row_index in range(len(review_rows)):
            try:
                review_rows = browser.find_elements(By.CSS_SELECTOR, "tbody#feedbackTableBody tr")
                current_row = review_rows[row_index]
                star_container = current_row.find_element(By.CSS_SELECTOR, "td.rating-cell div.star-rating")
                star_labels = star_container.find_elements(By.TAG_NAME, "label")
                
                if len(star_labels) == 0:
                    print(f"Warning: No star labels found for question {row_index + 1}")
                    continue
                
                rating_index = randint(max(0, len(star_labels) - 2), len(star_labels) - 1)
                star_to_click = star_labels[rating_index]
                browser.execute_script("arguments[0].scrollIntoView(true);", star_to_click)
                time.sleep(0.2)
                browser.execute_script("arguments[0].click();", star_to_click)
                
            except Exception as e:
                print(f"Warning: Could not rate question {row_index + 1}: {str(e)}")
                continue
        
        try:
            submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnSave")))
            browser.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(0.5)
            browser.execute_script("arguments[0].click();", submit_button)
            print(f"Submitted feedback for staff {i+1}/{num_staff}")
            time.sleep(2)
        except Exception as e:
            print(f"Warning: Could not submit feedback for staff {i+1}: {str(e)}")
    
    print("Clicking final submit button...")
    try:
        final_submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnFinalSubmit")))
        browser.execute_script("arguments[0].scrollIntoView(true);", final_submit_button)
        time.sleep(0.5)
        browser.execute_script("arguments[0].click();", final_submit_button)
        print("Final submission successful!")
        time.sleep(2)
    except TimeoutException:
        raise Exception("Could not find final submit button")
