import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Load Environment Variables ---
# This line loads credentials from your .env file
load_dotenv()

# --- Configuration ---
# The URL for the iframe that contains the login form.
HPL_LOGIN_FRAME_URL = "https://lcr.houstonlibrary.org/validate_form_nyt"
# The URL the form's JavaScript sends the validation request to.
HPL_VALIDATION_URL = "https://lcr.houstonlibrary.org/jquery/jq_validate_search.php"


def get_initial_redeem_url():
    """
    Logs into the Houston Public Library to get the initial NYT redeem URL.
    This part is still faster without a full browser.

    Returns:
        str: The URL for the NYT redeem page, or None if an error occurs.
    """
    print("--- Step 1: Authenticating with Houston Public Library ---")
    try:
        card_number = os.environ['HPL_CARD']
        pin = os.environ['HPL_PIN']
    except KeyError as e:
        print(f"Error: Environment variable {e} not set.")
        print("Please make sure you have a .env file with HPL_CARD and HPL_PIN set.")
        sys.exit(1)

    with requests.Session() as session:
        try:
            print(f"Fetching login page: {HPL_LOGIN_FRAME_URL}")
            page_response = session.get(HPL_LOGIN_FRAME_URL)
            page_response.raise_for_status()
            soup = BeautifulSoup(page_response.text, 'html.parser')
            hidden_input = soup.find('input', {'id': 'v-url'})

            if not hidden_input or not hidden_input.get('value'):
                print("Error: Could not find the hidden 'v-url' input on the library login page.")
                sys.exit(1)

            final_nyt_url = hidden_input.get('value')
            print("Found hidden NYT URL.")

            print(f"Sending validation request...")
            validation_payload = {
                'connectType': 'nyt',
                'searchBarcode': card_number,
                'searchPincode': pin,
            }
            validation_response = session.post(HPL_VALIDATION_URL, json=validation_payload)
            validation_response.raise_for_status()

            if "SUCCESS" in validation_response.text.strip():
                print("Library validation successful!")
                return final_nyt_url
            else:
                print("Library validation failed. Please check HPL credentials in .env file.")
                return None

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the library login step: {e}")
            sys.exit(1)

def redeem_and_login_on_nyt(redeem_url):
    """
    Uses Selenium to open a browser, redeem the code, and log into the NYT website.
    Handles the two-step email/password login process.
    """
    print("\n--- Step 2: Automating New York Times Login ---")
    try:
        nyt_email = os.environ['NYT_EMAIL']
        nyt_password = os.environ['NYT_PASSWORD']
    except KeyError as e:
        print(f"Error: Environment variable {e} not set.")
        print("Please set NYT_EMAIL and NYT_PASSWORD in your .env file.")
        sys.exit(1)

    # --- FIX for Chrome driver version mismatch ---
    options = ChromeOptions()
    # This path is based on your terminal output and is still necessary.
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome Beta"
    
    # By using Service() without any arguments, Selenium will automatically
    # detect the required driver version for your browser and download it.
    service = ChromeService()
    
    # Initialize the driver with the service and options.
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"Navigating to the NYT redeem page...")
        driver.get(redeem_url)
        
        # Wait for the redeem page to load and click the redeem button
        redeem_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='btn-redeem']"))
        )
        redeem_button.click()
        print("Clicked the 'Redeem' button.")

        # -- Start of Two-Step Login --
        
        # STEP 1: Enter Email and click Continue
        print("Looking for the email input form...")
        email_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "email"))
        )
        print("Entering email address...")
        email_input.send_keys(nyt_email)
        
        # Find and click the 'Continue' button
        continue_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        continue_button.click()
        print("Clicked 'Continue'. Waiting for password page...")

        # STEP 2: Enter Password on the new page
        password_input = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "password"))
        )
        print("Entering password...")
        password_input.send_keys(nyt_password)

        # Find and click the final Log In button
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        print("Clicked 'Log In'.")

        # Wait for the login to complete and the page to potentially redirect
        print("\n✅ Login successful! Verifying final page...")
        WebDriverWait(driver, 30).until(
            EC.url_contains("nytimes.com") 
        )
        print("Final page loaded. Browser will close in 10 seconds.")
        time.sleep(10)

    except Exception as e:
        print(f"\nAn error occurred during the browser automation: {e}")
        print("The script will leave the browser open for 30 seconds for debugging.")
        time.sleep(30)
    finally:
        print("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    initial_url = get_initial_redeem_url()

    if initial_url:
        redeem_and_login_on_nyt(initial_url)
    else:
        print("\n❌ Could not retrieve the initial redeem URL. Aborting.")
