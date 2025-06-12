import os
import sys
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# --- Load Environment Variables ---
# This line loads the HPL_CARD and HPL_PIN from your .env file
load_dotenv()

# --- Configuration ---
# This is the direct URL to the login form, which is inside an iframe on the main page.
# We target this directly to simplify the process.
HPL_NYT_LOGIN_FORM_URL = "https://lcr.houstonlibrary.org/validate_form_nyt"


def get_nyt_pass_url():
    """
    Logs into the Houston Public Library website using credentials from
    environment variables and retrieves the unique NYT Group Pass URL.

    Returns:
        str: The full URL for the NYT pass, or None if an error occurs.
    """
    # --- 1. Get Credentials ---
    # For security, the script reads your library card number and PIN from
    # the .env file.
    try:
        card_number = os.environ['HPL_CARD']
        pin = os.environ['HPL_PIN']
    except KeyError as e:
        print(f"Error: Environment variable {e} not set.")
        print("Please make sure you have a .env file with HPL_CARD and HPL_PIN set.")
        sys.exit(1)

    # A session object is used to persist cookies across multiple requests,
    # which is essential for staying logged in.
    with requests.Session() as session:
        try:
            # --- 2. Log in to HPL via the NYT Login Form ---
            print(f"Accessing the NYT login form at: {HPL_NYT_LOGIN_FORM_URL}")
            print("Attempting to log in...")

            # This payload mimics the data submitted by the login form.
            login_payload = {
                'card_number': card_number,
                'pin': pin,
            }

            # We send a POST request directly to the form's URL.
            login_response = session.post(HPL_NYT_LOGIN_FORM_URL, data=login_payload)
            login_response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)

            # Check if the login was successful by looking for common failure messages
            if "invalid" in login_response.text.lower() or "could not be validated" in login_response.text.lower():
                print("Login failed. Please double-check your HPL_CARD and HPL_PIN in the .env file.")
                sys.exit(1)

            print("Login successful.")

            # --- DEBUGGING: Print the response to see its structure ---
            print("\n--- DEBUG: POST-LOGIN RESPONSE ---")
            print(f"Response URL: {login_response.url}")
            print("Response HTML:")
            print(login_response.text)
            print("--- END DEBUG ---")
            # We exit here for now so we can analyze the HTML.
            # Once fixed, we will remove this section.
            sys.exit(0) 
            # --- END DEBUGGING ---


            # --- 3. Extract the Final Pass URL ---
            # After a successful login, the response page contains a script that
            # redirects to the final NYT URL. We need to parse it out.
            soup = BeautifulSoup(login_response.text, 'html.parser')

            # The final URL is located inside a <script> tag.
            # We'll use a regex to find it.
            # The pattern looks for `window.parent.location.href = '...';`
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    match = re.search(r"window\.parent\.location\.href\s*=\s*['\"](https?://[^\s'\"]+)", script.string)
                    if match:
                        final_url = match.group(1)
                        return final_url.strip()

            print("Error: Could not find the final NYT pass URL after logging in.")
            print("The library website's post-login structure may have changed.")
            return None

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the web request: {e}")
            sys.exit(1)


if __name__ == "__main__":
    print("--- NYT Pass Auto-Renewal Script ---")
    pass_url = get_nyt_pass_url()

    if pass_url:
        print("\n✅ Successfully retrieved NYT Pass URL!")
        print("--------------------------------------------------")
        print(pass_url)
        print("--------------------------------------------------")
        print("\nVisit the URL above in your browser to activate your 72-hour pass.")
    else:
        print("\n❌ Failed to retrieve the NYT Pass URL.")
