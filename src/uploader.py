import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from src.config import get_config
from src.logger import get_logger

class YouTubeUploader:
    def __init__(self, profile_path=None):
        """
        Initializes the uploader.
        profile_path: Path to chrome user data directory to persist login.
        """
        config = get_config()
        self.logger = get_logger()
        
        self.options = webdriver.ChromeOptions()
        
        # Get profile path from config or argument
        profile_path = profile_path or config.get('upload.browser_profile')
        if profile_path:
            self.options.add_argument(f"user-data-dir={profile_path}")
            self.logger.debug(f"Using Chrome profile: {profile_path}")
        
        # Headless mode from config
        if config.get('upload.headless', False):
            self.options.add_argument("--headless")
        
        # Suppress errors
        self.options.add_argument("--log-level=3")
        
    def upload_video(self, video_path, title, description):
        """
        Uploads a video to YouTube.
        """
        self.logger.info(f"Starting upload for: {title}")
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=self.options)
        
        try:
            driver.get("https://studio.youtube.com")
            
            # Check if logged in by looking for "Create" button or similar
            # If redirected to login, wait user to login manually?
            # Creating a robust check.
            
            self.logger.info("Checking login status...")
            try:
                # Wait for the "Create" button or channel dashboard
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "upload-icon"))
                )
                self.logger.info("Logged in.")
            except:
                self.logger.warning("Not logged in. Please log in manually in the browser window.")
                self.logger.info("Waiting for login (check for 'upload-icon')...")
                # Infinite wait until user logs in? Or simple timeout?
                # Let's give them 60 seconds.
                try:
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.ID, "upload-icon"))
                    )
                    self.logger.info("Login detected.")
                except:
                    self.logger.error("Login timed out.")
                    return False
            
            # Click Upload button (usually the create button -> upload video)
            # Actually, navigating directly to upload page might work?
            # https://studio.youtube.com/channel/CHANNEL_ID/videos/upload?d=ud
            # But we don't know channel ID.
            
            # Let's look for the CREATE button.
            create_button = driver.find_element(By.ID, "create-icon")
            create_button.click()
            
            # Click "Upload videos" in the dropdown
            # This is fragile because selectors change.
            # Best way: send file directly to the input type=file if present invisible.
            
            upload_item = WebDriverWait(driver, 5).until(
                 EC.element_to_be_clickable((By.XPATH, "//ytcp-text-dropdown-trigger-element[contains(., 'Upload videos')]"))
            )
            # Actually the create menu items are usually in a paper-listbox
            # Let's try finding by text "Upload videos"
            
            # Better approach: The create button opens a dialogue? 
            # Often standard "Upload" button is visible on dashboard if empty, but usually top right "CREATE".
            
            # Let's try a different strategy:
            # wait for input[type=file] and send keys.
            # Usually hidden.
            time.sleep(1)
            
            # The 'Upload videos' menu item
            driver.execute_script("document.getElementById('text-item-0').click()") 
            # This is highly specific to structure.
            
            # Let's use the file input directly if we can find it.
            # Often it's loaded after clicking 'Create' -> 'Upload'.
            
            # Just click "Upload videos" text
            items = driver.find_elements(By.XPATH, "//*[text()='Upload videos']")
            for item in items:
                if item.is_displayed():
                    item.click()
                    break
            
            # Wait for file input
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(os.path.abspath(video_path))
            
            self.logger.info("Uploading file...")
            
            # Wait for upload to complete and metadata fields to appear
            title_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='title-textarea']//div[@contenteditable='true']"))
            )
            
            # Clear and set title (it usually auto-fills from filename)
            title_input.clear()
            title_input.send_keys(title)
            
            # Description
            desc_input = driver.find_element(By.XPATH, "//div[@id='description-textarea']//div[@contenteditable='true']")
            desc_input.clear()
            desc_input.send_keys(description)
            
            # Kids setting (Not made for kids)
            driver.find_element(By.NAME, "VIDEO_MADE_FOR_KIDS_NOT_MFK").click()
            
            # Next buttons
            for i in range(3):
                next_button = driver.find_element(By.ID, "next-button")
                next_button.click()
                time.sleep(1)
            
            # Visibility: Private for safety, or Public? 
            # Let's choose "Private" or "Unlisted" for now.
            driver.find_element(By.NAME, "PRIVATE").click() # or UNLISTED
            
            # Save
            save_button = driver.find_element(By.ID, "done-button")
            save_button.click()
            
            self.logger.info("Upload complete. Waiting for processing...")
            time.sleep(5)
            
            return True

        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            return False
        finally:
            # keep browser open for debug or close?
            # driver.quit()
            pass

if __name__ == "__main__":
    # Test
    pass
