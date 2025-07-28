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
    Sets up and returns a Selenium WebDriver instance for Chrome.
    Configured to run headlessly in a containerized environment like Docker.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def run_feedback_automation(index, rollno, password, status_queue):
    """
    Main function to orchestrate the feedback automation process.
    It reports its progress back to the main app via the status_queue.
    Includes debugging steps like saving screenshots on failure.
    """
    browser = None
    try:
        status_queue.put({"status": "running", "progress": 0, "message": "Initializing browser..."})
        browser = create_driver()
        wait = WebDriverWait(browser, 20)

        status_queue.put({"status": "running", "progress": 5, "message": "Accessing login page..."})
        browser.get("https://ecampus.psgtech.ac.in/studzone")

        status_queue.put({"status": "running", "progress": 10, "message": "Entering credentials..."})
        rollno_field = wait.until(EC.presence_of_element_located((By.ID, "rollno")))
        rollno_field.send_keys(rollno)
        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(password)
        checkbox = browser.find_element(By.ID, "terms")
        browser.execute_script("arguments[0].click();", checkbox)
        login_button = browser.find_element(By.ID, "btnLogin")
        browser.execute_script("arguments[0].click();", login_button)
        
        status_queue.put({"status": "running", "progress": 20, "message": "Login successful. Navigating dashboard..."})
        
        feedback_card = wait.until(EC.element_to_be_clickable((By.XPATH, f"//h5[text()='Feedback']")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", feedback_card)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
        feedbacks = browser.find_elements(By.CLASS_NAME, "card-body")
        
        status_queue.put({"status": "running", "progress": 30, "message": "Selecting feedback form..."})
        browser.execute_script("arguments[0].click();", feedbacks[index])
        
        if index == 0:
            endsem_form(browser, status_queue)
        else:
            intermediate_form(browser, status_queue)
            
        status_queue.put({"status": "done", "progress": 100, "message": "Feedback submitted successfully!"})

    except TimeoutException as e:
        # Save debugging info if any timeout occurs
        if browser:
            browser.save_screenshot("debug_screenshot.png")
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(browser.page_source)
        status_queue.put({"status": "error", "message": f"A timeout occurred: {e}. Check credentials or website status. Debug files saved locally."})
    except Exception as e:
        status_queue.put({"status": "error", "message": f"An unexpected error occurred: {str(e)}"})
    finally:
        if browser:
            browser.quit()


def intermediate_form(browser, status_queue):
    wait = WebDriverWait(browser, 15) # Slightly longer wait
    courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
    if not courses:
        raise Exception("No intermediate feedback courses found.")

    num_courses = len(courses)
    for i in range(num_courses):
        courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
        course_names = browser.find_elements(By.CSS_SELECTOR, "h6.course")
        progress = 30 + int(60 * (i / num_courses))
        status_queue.put({"status": "running", "progress": progress, "message": f"Processing: {course_names[i].text}"})
        
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", courses[i])
        
        try:
            # This is the new debugging block. It waits for the question counter.
            questions_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.bottom-0"))).text
        except TimeoutException:
            # If it fails, save a screenshot of the form itself.
            browser.save_screenshot("debug_form_screenshot.png")
            with open("debug_form_source.html", "w", encoding="utf-8") as f:
                f.write(browser.page_source)
            raise TimeoutException("Could not find the questions inside the feedback form. Debug files saved locally.")

        questions = int(questions_text.split()[-1])
        clicks = 0
        while clicks < questions:
            try:
                radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[@for='radio-{clicks + 1}-1']")))
                browser.execute_script("arguments[0].click();", radio_button)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='carousel-control-next']")))
                browser.execute_script("arguments[0].click();", next_button)
                clicks += 1
                time.sleep(0.3) # Slightly increased delay
            except StaleElementReferenceException:
                continue
        back_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "overlay")))
        browser.execute_script("arguments[0].click();", back_button)
        time.sleep(0.5)

def endsem_form(browser, status_queue):
    wait = WebDriverWait(browser, 15)
    try:
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
    except TimeoutException:
        raise Exception("Could not find the list of staff for feedback.")

    num_staff = len(staff_list)
    for i in range(num_staff):
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
        course_name = staff_list[i].find_element(By.CSS_SELECTOR, "span.ms-1").text
        progress = 30 + int(60 * (i / num_staff))
        status_queue.put({"status": "running", "progress": progress, "message": f"Processing: {course_name}"})
        
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", staff_list[i])
        
        try:
            # New debugging block for the end-sem form
            wait.until(EC.presence_of_element_located((By.ID, "feedbackTableBody")))
        except TimeoutException:
            browser.save_screenshot("debug_form_screenshot.png")
            with open("debug_form_source.html", "w", encoding="utf-8") as f:
                f.write(browser.page_source)
            raise TimeoutException("Could not find the feedback table. Debug files saved locally.")

        review_list = browser.find_elements(By.CSS_SELECTOR, "td.question-cell")
        for count in range(1, len(review_list) + 1):
            star_button = browser.find_element(By.XPATH, f"//tbody[@id='feedbackTableBody']/tr[{count}]/td[@class='rating-cell']/div[@class='star-rating']/label[{randint(1, 2)}]")
            browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", star_button)
        submit_button = browser.find_element(By.ID, "btnSave")
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", submit_button)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img.img-fluid")))
        time.sleep(1)

    status_queue.put({"status": "running", "progress": 95, "message": "Finalizing submission..."})
    final_submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnFinalSubmit")))
    browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", final_submit_button)
