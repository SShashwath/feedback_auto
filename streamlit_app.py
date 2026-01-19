import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import time

st.set_page_config(
    page_title="Feedback Automation",
    page_icon="📝",
    layout="centered"
)

st.title("📝 Feedback Automation")
st.markdown("Automate your PSG Tech feedback submission")

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 1  # 1 = login, 2 = select feedback, 3 = done
if 'teachers' not in st.session_state:
    st.session_state.teachers = []
if 'feedback_choices' not in st.session_state:
    st.session_state.feedback_choices = {}


def create_driver():
    """Sets up Selenium WebDriver for Streamlit Cloud (uses Chromium)."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = "/usr/bin/chromium"
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def fetch_teachers(rollno, password, feedback_type, status_text):
    """Login and fetch the list of teachers/subjects."""
    browser = None
    teachers = []
    try:
        status_text.text("🔄 Initializing browser...")
        browser = create_driver()
        wait = WebDriverWait(browser, 20)

        status_text.text("🔄 Accessing login page...")
        browser.get("https://ecampus.psgtech.ac.in/studzone")

        status_text.text("🔄 Logging in...")
        rollno_field = wait.until(EC.presence_of_element_located((By.ID, "rollno")))
        rollno_field.send_keys(rollno)
        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(password)
        checkbox = browser.find_element(By.ID, "terms")
        browser.execute_script("arguments[0].click();", checkbox)
        login_button = browser.find_element(By.ID, "btnLogin")
        browser.execute_script("arguments[0].click();", login_button)

        status_text.text("🔄 Navigating to feedback section...")
        feedback_card = wait.until(EC.element_to_be_clickable((By.XPATH, "//h5[text()='Feedback']")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", feedback_card)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
        feedbacks = browser.find_elements(By.CLASS_NAME, "card-body")
        browser.execute_script("arguments[0].click();", feedbacks[feedback_type])

        status_text.text("🔄 Fetching teachers list...")
        
        if feedback_type == 0:  # End semester
            staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
            for staff in staff_list:
                name = staff.find_element(By.CSS_SELECTOR, "span.ms-1").text
                teachers.append({"name": name, "type": "endsem"})
        else:  # Intermediate
            courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
            course_names = browser.find_elements(By.CSS_SELECTOR, "h6.course")
            for i, course in enumerate(course_names):
                teachers.append({"name": course.text, "type": "intermediate"})

        status_text.text("✅ Teachers fetched successfully!")
        return teachers, None

    except TimeoutException:
        return None, "Login failed or page timeout. Check credentials."
    except Exception as e:
        return None, str(e)
    finally:
        if browser:
            browser.quit()


def submit_feedback(rollno, password, feedback_type, choices, progress_bar, status_text):
    """Submit feedback based on user choices."""
    browser = None
    try:
        progress_bar.progress(0)
        status_text.text("🔄 Initializing browser...")
        browser = create_driver()
        wait = WebDriverWait(browser, 20)

        progress_bar.progress(5)
        status_text.text("🔄 Logging in...")
        browser.get("https://ecampus.psgtech.ac.in/studzone")

        rollno_field = wait.until(EC.presence_of_element_located((By.ID, "rollno")))
        rollno_field.send_keys(rollno)
        password_field = browser.find_element(By.ID, "password")
        password_field.send_keys(password)
        checkbox = browser.find_element(By.ID, "terms")
        browser.execute_script("arguments[0].click();", checkbox)
        login_button = browser.find_element(By.ID, "btnLogin")
        browser.execute_script("arguments[0].click();", login_button)

        progress_bar.progress(15)
        status_text.text("🔄 Navigating to feedback...")
        feedback_card = wait.until(EC.element_to_be_clickable((By.XPATH, "//h5[text()='Feedback']")))
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", feedback_card)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card-body")))
        feedbacks = browser.find_elements(By.CLASS_NAME, "card-body")
        browser.execute_script("arguments[0].click();", feedbacks[feedback_type])

        progress_bar.progress(25)
        
        if feedback_type == 0:  # End semester
            submit_endsem_feedback(browser, wait, choices, progress_bar, status_text)
        else:  # Intermediate
            submit_intermediate_feedback(browser, wait, choices, progress_bar, status_text)

        progress_bar.progress(100)
        status_text.text("✅ Feedback submitted successfully!")
        return True

    except Exception as e:
        status_text.text(f"❌ Error: {str(e)}")
        return False
    finally:
        if browser:
            browser.quit()


def submit_endsem_feedback(browser, wait, choices, progress_bar, status_text):
    """Submit end semester feedback with user choices."""
    staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
    num_staff = len(staff_list)
    
    for i in range(num_staff):
        staff_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.staff-item")))
        course_name = staff_list[i].find_element(By.CSS_SELECTOR, "span.ms-1").text
        
        # Get user's choice for this teacher (default to good)
        rating = choices.get(course_name, "good")
        # Good = stars 4-5 (labels 1-2), Bad = stars 1-2 (labels 4-5)
        star_range = (1, 2) if rating == "good" else (4, 5)
        
        progress = 25 + int(65 * (i / num_staff))
        progress_bar.progress(progress)
        status_text.text(f"🔄 Processing: {course_name} ({rating})")
        
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", staff_list[i])
        wait.until(EC.presence_of_element_located((By.ID, "feedbackTableBody")))
        review_list = browser.find_elements(By.CSS_SELECTOR, "td.question-cell")
        
        for count in range(1, len(review_list) + 1):
            import random
            star_label = random.randint(star_range[0], star_range[1])
            star_button = browser.find_element(By.XPATH, f"//tbody[@id='feedbackTableBody']/tr[{count}]/td[@class='rating-cell']/div[@class='star-rating']/label[{star_label}]")
            browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", star_button)
        
        submit_button = browser.find_element(By.ID, "btnSave")
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", submit_button)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img.img-fluid")))
        time.sleep(1)

    progress_bar.progress(95)
    status_text.text("🔄 Finalizing submission...")
    final_submit_button = wait.until(EC.element_to_be_clickable((By.ID, "btnFinalSubmit")))
    browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click()", final_submit_button)


def get_option_for_question(question_num, rating, num_options):
    """
    Get the appropriate option for each question based on rating.
    
    Question mapping:
    - Q1-3, Q7: Self-assessment (always option 1 - positive)
    - Q4: Self-assessment reversed (Good→last, Bad→1)
    - Q5, Q6, Q8-11: Teacher-related (Good→1, Bad→last)
    """
    if rating == "good":
        if question_num == 4:
            return num_options  # For good feedback, blame yourself (last option)
        else:
            return 1  # First option for all others
    else:  # bad
        if question_num in [1, 2, 3, 7]:
            return 1  # Self-assessment: still pick positive (option 1)
        elif question_num == 4:
            return 1  # Blame course (need more time)
        else:  # Q5, Q6, Q8, Q9, Q10, Q11 - teacher related
            return num_options  # Last option (Disagree/Inadequate)


def submit_intermediate_feedback(browser, wait, choices, progress_bar, status_text):
    """Submit intermediate feedback with user choices using smart question mapping."""
    courses = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "intermediate-body")))
    num_courses = len(courses)

    # Number of options per question (based on observed form)
    question_options = {
        1: 2,   # Strongly agree, Agree
        2: 3,   # >85%, 75-85%, <75%
        3: 4,   # 4 learning options
        4: 2,   # need time, lack of prep
        5: 3,   # Strongly agree, Agree, Disagree
        6: 3,   # Adequate, Inadequate, Too much
        7: 3,   # Strongly agree, Agree, Disagree
        8: 3,   # Strongly agree, Agree, Disagree
        9: 3,   # Strongly agree, Agree, Disagree
        10: 3,  # Strongly agree, Agree, Disagree
        11: 3,  # Strongly agree, Agree, Disagree
    }

    for i in range(num_courses):
        courses = browser.find_elements(By.CLASS_NAME, "intermediate-body")
        course_names = browser.find_elements(By.CSS_SELECTOR, "h6.course")
        course_name = course_names[i].text
        
        # Get user's choice (default to good)
        rating = choices.get(course_name, "good")
        
        progress = 25 + int(65 * (i / num_courses))
        progress_bar.progress(progress)
        status_text.text(f"🔄 Processing: {course_name} ({rating})")
        
        browser.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", courses[i])
        questions_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.bottom-0"))).text
        questions = int(questions_text.split()[-1])
        
        clicks = 0
        while clicks < questions:
            try:
                question_num = clicks + 1
                num_options = question_options.get(question_num, 3)  # Default to 3 options
                option = get_option_for_question(question_num, rating, num_options)
                
                radio_button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//label[@for='radio-{question_num}-{option}']")))
                browser.execute_script("arguments[0].click();", radio_button)
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='carousel-control-next']")))
                browser.execute_script("arguments[0].click();", next_button)
                clicks += 1
                time.sleep(0.2)
            except StaleElementReferenceException:
                continue
        
        back_button = browser.find_element(By.CLASS_NAME, "overlay")
        browser.execute_script("arguments[0].click();", back_button)
        time.sleep(0.5)


# ==================== UI FLOW ====================

if st.session_state.step == 1:
    # Step 1: Login and fetch teachers
    st.subheader("Step 1: Login & Fetch Teachers")
    
    rollno = st.text_input("Roll Number", placeholder="e.g., 23z309", key="rollno")
    password = st.text_input("Password", type="password", key="password")
    feedback_type = st.selectbox(
        "Feedback Type",
        options=[("End Semester Feedback", 0), ("Intermediate Feedback", 1)],
        format_func=lambda x: x[0],
        key="feedback_type"
    )
    
    if st.button("🔍 Fetch Teachers", type="primary", disabled=not (rollno and password)):
        status_text = st.empty()
        with st.spinner("Fetching teachers..."):
            teachers, error = fetch_teachers(rollno, password, feedback_type[1], status_text)
        
        if error:
            st.error(f"❌ {error}")
        elif teachers:
            st.session_state.teachers = teachers
            st.session_state.stored_rollno = rollno
            st.session_state.stored_password = password
            st.session_state.stored_feedback_type = feedback_type[1]
            # Initialize all to "good" by default
            for t in teachers:
                st.session_state.feedback_choices[t['name']] = "good"
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    # Step 2: Select feedback for each teacher
    st.subheader("Step 2: Select Feedback for Each Teacher")
    st.markdown("Choose **Good 👍** or **Bad 👎** for each teacher:")
    
    st.markdown("---")
    
    for i, teacher in enumerate(st.session_state.teachers):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{teacher['name']}**")
        with col2:
            choice = st.selectbox(
                f"Rating for {teacher['name']}",
                options=["good", "bad"],
                format_func=lambda x: "👍 Good" if x == "good" else "👎 Bad",
                key=f"choice_{i}",
                label_visibility="collapsed"
            )
            st.session_state.feedback_choices[teacher['name']] = choice
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.step = 1
            st.session_state.teachers = []
            st.session_state.feedback_choices = {}
            st.rerun()
    with col2:
        if st.button("🚀 Submit Feedback", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success = submit_feedback(
                st.session_state.stored_rollno,
                st.session_state.stored_password,
                st.session_state.stored_feedback_type,
                st.session_state.feedback_choices,
                progress_bar,
                status_text
            )
            
            if success:
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    # Step 3: Success
    st.success("🎉 Feedback submitted successfully!")
    st.balloons()
    
    if st.button("🔄 Start Over"):
        st.session_state.step = 1
        st.session_state.teachers = []
        st.session_state.feedback_choices = {}
        st.rerun()

st.markdown("---")
st.caption("⚠️ This tool is for educational purposes only. Use responsibly.")
