#!/usr/bin/env python3
"""
JazzHR Resume Downloader - Browser Automation

This script uses Selenium to navigate the JazzHR web interface and download
all resumes for a specific job by accessing each candidate profile.
"""

import os
import sys
import time
import logging
import re
import json
from pathlib import Path
from typing import List, Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_resumes_browser.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class JazzHRBrowserDownloader:
    """Browser automation class for downloading resumes from JazzHR."""
    
    def __init__(self, job_id: str, output_dir: str = "resumes", cookies: Optional[List[Dict]] = None):
        """
        Initialize the browser downloader.
        
        Args:
            job_id: The job ID to download resumes for
            output_dir: Base directory for downloaded resumes
            cookies: Optional list of cookies to load into browser (for authentication)
        """
        self.job_id = job_id
        self.output_dir = Path(output_dir) / f"job_{job_id}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self.downloaded_count = 0
        self.failed_count = 0
        self.downloaded_files = []  # Track successfully downloaded files
        self.downloaded_candidate_ids = set()  # Track unique candidate IDs downloaded
        self.all_candidate_ids = set()  # Track all candidate IDs found
        self.cancelled = False  # Flag to check for cancellation
        self.cookies = cookies  # Store cookies for authentication
        
    def setup_driver(self):
        """Set up Chrome WebDriver with download preferences."""
        chrome_options = Options()
        
        # Configure download preferences
        download_dir = str(self.output_dir.absolute())
        logger.info(f"Configuring download directory: {download_dir}")
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Also set download behavior
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use headless mode in production (when DISPLAY is set or HEADLESS env var is set)
        # In local development, headless is disabled so user can login if needed
        use_headless = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("DISPLAY") is not None
        if use_headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--headless=new")  # Use new headless mode
            logger.info("Running in headless mode")
        else:
            logger.info("Running in non-headless mode (user can login if needed)")
        
        # Other useful options (required for Docker/containerized environments)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.maximize_window()
            logger.info("Chrome WebDriver initialized successfully")
            
            # Load cookies if provided (for authentication in headless mode)
            if self.cookies:
                self.load_cookies()
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def load_cookies(self):
        """Load cookies into the browser for authentication."""
        if not self.cookies:
            return
        
        try:
            logger.info("Loading authentication cookies...")
            # First navigate to the domain to set cookies
            self.driver.get("https://app.jazz.co")
            time.sleep(2)
            
            # Add each cookie
            for cookie in self.cookies:
                try:
                    # Ensure cookie has required fields
                    if 'name' in cookie and 'value' in cookie:
                        # Remove 'expiry' if it's too large (Selenium limitation)
                        cookie_to_add = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie.get('domain', '.jazz.co'),
                            'path': cookie.get('path', '/'),
                        }
                        # Only add secure/httpOnly if they exist
                        if 'secure' in cookie:
                            cookie_to_add['secure'] = cookie['secure']
                        if 'httpOnly' in cookie:
                            cookie_to_add['httpOnly'] = cookie['httpOnly']
                        
                        self.driver.add_cookie(cookie_to_add)
                        logger.debug(f"Added cookie: {cookie['name']}")
                except Exception as e:
                    logger.warning(f"Failed to add cookie {cookie.get('name', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully loaded {len(self.cookies)} cookies")
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            raise
    
    def check_login_required(self) -> bool:
        """
        Check if login is required by looking for login elements.
        
        Returns:
            True if login appears to be required, False otherwise
        """
        try:
            current_url = self.driver.current_url
            logger.debug(f"Checking login status. Current URL: {current_url}")
            
            # Check URL first - if we're on the candidate page, we're likely logged in
            if f"/job/{self.job_id}/candidate" in current_url:
                logger.debug("Already on candidate page - likely logged in")
                return False
            
            # Check URL for login page
            if "login" in current_url.lower() or "signin" in current_url.lower():
                logger.info("Currently on login page")
                return True
            
            # Look for common login indicators
            login_indicators = [
                "//input[@type='email']",
                "//input[@type='password']",
                "//button[contains(text(), 'Sign in')]",
                "//button[contains(text(), 'Log in')]",
                "//a[contains(text(), 'Sign in')]",
                "//a[contains(text(), 'Log in')]"
            ]
            
            for xpath in login_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        logger.info(f"Login indicator found: {xpath}")
                        return True
                except NoSuchElementException:
                    continue
            
            # If we get here, no login indicators found
            logger.debug("No login indicators found - assuming logged in")
            return False
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            # If we can't determine, assume not logged in to be safe
            return False
    
    def wait_for_login(self):
        """Wait for user to manually complete login by automatically detecting when login is done."""
        logger.info("=" * 60)
        logger.info("LOGIN REQUIRED")
        logger.info("=" * 60)
        logger.info("Please log in to JazzHR in the browser window.")
        logger.info("The script will automatically detect when login is complete.")
        logger.info("=" * 60)
        
        # Wait for login to complete automatically (polling)
        max_wait = 600  # Wait up to 10 minutes
        wait_time = 0
        check_interval = 3  # Check every 3 seconds
        
        while wait_time < max_wait:
            # Check for cancellation
            if self.cancelled:
                logger.info("Download cancelled during login wait")
                return False
            
            time.sleep(check_interval)
            wait_time += check_interval
            
            # Check if login is complete
            if not self.check_login_required():
                logger.info("Login detected. Continuing with download process...")
                # Wait a bit more for page to fully load after login
                time.sleep(3)
                return True
            
            # Log progress every 15 seconds
            if wait_time % 15 == 0:
                logger.info(f"Waiting for login to complete... ({wait_time}s elapsed)")
        
        # Timeout reached
        logger.error("Login timeout after 10 minutes. Please ensure you are logged in and try again.")
        return False
    
    def navigate_to_candidate_list(self):
        """Navigate to the candidate list page for the job."""
        url = f"https://app.jazz.co/app/v2/job/{self.job_id}/candidate?workflowStep=1"
        logger.info(f"Navigating to: {url}")
        self.driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Check if login is required
        login_required = self.check_login_required()
        logger.info(f"Login required check: {login_required}")
        
        if login_required:
            # Check if we're in headless mode
            use_headless = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("DISPLAY") is not None
            
            if use_headless and not self.cookies:
                logger.error("=" * 60)
                logger.error("LOGIN REQUIRED IN HEADLESS MODE")
                logger.error("=" * 60)
                logger.error("Cannot perform manual login in headless mode.")
                logger.error("Please provide authentication cookies via:")
                logger.error("1. JAZZHR_COOKIES environment variable (JSON string)")
                logger.error("2. Or cookies parameter when calling the API")
                logger.error("=" * 60)
                raise Exception("Login required but no cookies provided for headless mode")
            
            if not use_headless:
                logger.info("Login is required. Waiting for user to log in...")
                login_success = self.wait_for_login()
                if not login_success:
                    logger.error("Login failed or timed out. Cannot continue with download.")
                    raise Exception("Login failed or timed out")
            else:
                # In headless mode with cookies, try reloading page
                logger.info("Reloading page with cookies...")
                self.driver.get(url)
                time.sleep(5)
                # Check again if login is still required
                if self.check_login_required():
                    logger.error("Cookies provided but login still required. Cookies may be invalid or expired.")
                    raise Exception("Authentication failed: Invalid or expired cookies")
            # Navigate again after login
            logger.info("Navigating to candidate list after successful login...")
            self.driver.get(url)
            time.sleep(5)
            
            # Verify we're on the right page
            if self.check_login_required():
                logger.error("Still on login page after login attempt. Cannot continue.")
                raise Exception("Login verification failed")
        else:
            logger.info("Already logged in. Proceeding with download...")
    
    def scroll_to_load_all_candidates(self):
        """Scroll the page to load all candidates (handle infinite scroll or pagination)."""
        logger.info("Scrolling to load all candidates...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 50  # Prevent infinite loops
        no_change_count = 0
        
        while scroll_attempts < max_scroll_attempts:
            # Check for cancellation
            if self.cancelled:
                return
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:  # No change for 3 scrolls, probably done
                    logger.info("No new content loaded, scrolling complete")
                    break
            else:
                no_change_count = 0
                logger.debug(f"Content loaded, height changed from {last_height} to {new_height}")
            
            last_height = new_height
            scroll_attempts += 1
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        logger.info(f"Finished scrolling after {scroll_attempts} attempts")
    
    def is_candidate_not_hired(self, element) -> bool:
        """
        Check if a candidate has "Not Hired" status.
        
        Args:
            element: WebElement containing candidate link or row
            
        Returns:
            True if candidate is marked as "Not Hired", False otherwise
        """
        try:
            # First, try quick check: look for "Not Hired" class in the element itself or immediate parent
            try:
                # Check the element itself
                classes = element.get_attribute("class") or ""
                if "is-workflow-not-hired" in classes or "not-hired" in classes.lower():
                    return True
                
                # Check immediate parent (most common case)
                try:
                    parent = element.find_element(By.XPATH, "./..")
                    parent_classes = parent.get_attribute("class") or ""
                    if "is-workflow-not-hired" in parent_classes:
                        return True
                    
                    # Quick check for workflow tags in parent
                    not_hired_tags = parent.find_elements(By.CSS_SELECTOR, ".is-workflow-not-hired, .jz-tag.is-workflow-not-hired")
                    if not_hired_tags:
                        return True
                except:
                    pass
            except:
                pass
            
            # If quick check didn't find it, try finding the row/container
            try:
                # Try to find the row/container (go up to 3 levels max for performance)
                parent = element
                for level in range(3):
                    try:
                        # Check for workflow status tags in this level
                        not_hired_elements = parent.find_elements(By.CSS_SELECTOR, ".is-workflow-not-hired")
                        if not_hired_elements:
                            return True
                        
                        # Check text in workflow tags only (more specific)
                        workflow_tags = parent.find_elements(By.CSS_SELECTOR, ".jz-tag.is-workflow-not-hired, .jz-tag[class*='workflow']")
                        for tag in workflow_tags:
                            tag_text = tag.text.lower()
                            if "not hired" in tag_text:
                                return True
                        
                        # Move to parent
                        parent = parent.find_element(By.XPATH, "./..")
                    except:
                        break
            except:
                pass
            
            return False
        except Exception as e:
            # If any error occurs, assume not "Not Hired" (safer to include than exclude)
            return False
    
    def get_candidate_links(self) -> List[str]:
        """
        Extract all candidate profile links from the page, handling pagination/infinite scroll.
        Excludes candidates with "Not Hired" status.
        
        Returns:
            List of candidate profile URLs (excluding Not Hired candidates)
        """
        candidate_links = []
        candidate_ids = set()
        excluded_count = 0
        
        try:
            # Wait for candidate list to load
            wait = WebDriverWait(self.driver, 30)
            time.sleep(3)  # Give page time to fully load
            
            # Scroll to load all candidates (handle infinite scroll)
            logger.info("Scrolling to load all candidates first...")
            self.scroll_to_load_all_candidates()
            logger.info("Scrolling complete. Now extracting candidate links...")
            
            # Try multiple selectors for candidate links
            selectors = [
                "a[href*='/candidate/']",
                "a[href*='/applicant/']",
                ".candidate-link",
                ".applicant-link",
                "[data-candidate-id]",
                "tr[data-candidate-id] a",
                ".candidate-row a",
                ".applicant-row a"
            ]
            
            candidate_elements = []
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} candidate links using selector: {selector}")
                        candidate_elements = elements
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no links found, try to find clickable rows
            if not candidate_elements:
                logger.info("Trying to find candidate rows...")
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "tr, .candidate-row, .applicant-row")
                    for row in rows:
                        try:
                            link = row.find_element(By.TAG_NAME, "a")
                            if link:
                                candidate_elements.append(link)
                        except:
                            # Row might be clickable itself
                            if row.get_attribute("onclick") or row.get_attribute("data-href"):
                                candidate_elements.append(row)
                except Exception as e:
                    logger.warning(f"Could not find candidate rows: {e}")
            
            # Process each candidate element and filter out "Not Hired" candidates
            total_elements = len(candidate_elements)
            logger.info(f"Processing {total_elements} candidate elements...")
            
            # Use a dict to deduplicate by candidate ID early
            candidate_dict = {}  # candidate_id -> (href, element)
            
            for idx, elem in enumerate(candidate_elements):
                if (idx + 1) % 100 == 0:
                    logger.info(f"Processed {idx + 1}/{total_elements} candidates...")
                
                try:
                    # Extract href first (faster than checking status)
                    if hasattr(elem, 'get_attribute'):
                        href = elem.get_attribute("href")
                    else:
                        href = str(elem) if isinstance(elem, str) else None
                    
                    if not href or ("candidate" not in href and "applicant" not in href):
                        continue
                    
                    # Extract candidate ID for deduplication
                    match = re.search(r'/candidate/(\d+)', href)
                    if not match:
                        continue
                    
                    candidate_id = match.group(1)
                    
                    # Skip if we've already seen this candidate ID
                    if candidate_id in candidate_dict:
                        continue
                    
                    # Check if this candidate is marked as "Not Hired"
                    if self.is_candidate_not_hired(elem):
                        excluded_count += 1
                        if excluded_count <= 10:  # Log first 10 exclusions
                            logger.debug(f"Excluding Not Hired candidate ID: {candidate_id}")
                        continue
                    
                    # Store candidate
                    candidate_dict[candidate_id] = href
                    
                except Exception as e:
                    logger.debug(f"Error processing candidate element {idx + 1}: {e}")
                    continue
            
            # Convert dict to list
            candidate_links = list(candidate_dict.values())
            candidate_ids = set(candidate_dict.keys())
            
            logger.info(f"Finished processing. Found {len(candidate_links)} unique valid candidates, excluded {excluded_count} 'Not Hired' candidates.")
            
            # Normalize URLs to always use /profile endpoint
            normalized_links = []
            for link in candidate_links:
                if isinstance(link, str) and link.startswith("http"):
                    # Extract candidate ID from URL
                    match = re.search(r'/candidate/(\d+)', link)
                    if match:
                        candidate_id = match.group(1)
                        # Construct profile URL
                        profile_url = f"https://app.jazz.co/app/v2/job/{self.job_id}/candidate/{candidate_id}/profile"
                        normalized_links.append(profile_url)
                    else:
                        # Keep original if we can't parse it
                        normalized_links.append(link)
                else:
                    # Keep non-string links as-is (WebElements)
                    normalized_links.append(link)
            
            self.all_candidate_ids = candidate_ids
            logger.info(f"Found {len(normalized_links)} unique candidate profile links ({len(candidate_ids)} unique candidate IDs)")
            if excluded_count > 0:
                logger.info(f"Excluded {excluded_count} candidate(s) with 'Not Hired' status")
            
            return normalized_links
            
        except Exception as e:
            logger.error(f"Error extracting candidate links: {e}")
            return []
    
    def get_downloaded_files(self) -> List[Path]:
        """
        Get list of files currently in the download directory.
        
        Returns:
            List of Path objects for files in download directory
        """
        files = []
        if self.output_dir.exists():
            files = [f for f in self.output_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
        return files
    
    def check_chrome_downloads_folder(self) -> List[Path]:
        """
        Check Chrome's default Downloads folder for recently downloaded files.
        
        Returns:
            List of recently downloaded PDF files
        """
        downloads_dir = Path.home() / "Downloads"
        if not downloads_dir.exists():
            return []
        
        # Get files modified in the last 2 minutes
        current_time = time.time()
        recent_files = []
        
        for file in downloads_dir.glob("*.pdf"):
            try:
                mtime = file.stat().st_mtime
                if current_time - mtime < 120:  # Last 2 minutes
                    recent_files.append(file)
            except:
                pass
        
        return recent_files
    
    def verify_download(self, wait_time: int = 10, check_interval: float = 0.5) -> bool:
        """
        Verify that a file was downloaded successfully.
        
        Args:
            wait_time: Maximum time to wait for download (seconds)
            check_interval: Time between checks (seconds)
            
        Returns:
            True if new file found, False otherwise
        """
        # Get initial file count and names
        initial_files = set(self.get_downloaded_files())
        initial_count = len(initial_files)
        
        # Wait for download to complete
        start_time = time.time()
        while time.time() - start_time < wait_time:
            current_files = set(self.get_downloaded_files())
            new_files = current_files - initial_files
            
            if new_files:
                # Found new file(s)
                for new_file in new_files:
                    # Check file size (should be > 0)
                    file_size = new_file.stat().st_size
                    if file_size > 0:
                        logger.info(f"✓ Verified download: {new_file.name} ({file_size:,} bytes)")
                        self.downloaded_files.append(new_file)
                        return True
                    else:
                        logger.warning(f"Downloaded file is empty: {new_file.name}")
            
            time.sleep(check_interval)
        
        # Check if count increased (might be a file with same name)
        final_count = len(self.get_downloaded_files())
        if final_count > initial_count:
            logger.info(f"File count increased from {initial_count} to {final_count}")
            # Get the newest file
            files = sorted(self.get_downloaded_files(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                newest = files[0]
                file_size = newest.stat().st_size
                if file_size > 0:
                    logger.info(f"✓ Verified download: {newest.name} ({file_size:,} bytes)")
                    self.downloaded_files.append(newest)
                    return True
        
        # Check Chrome's default Downloads folder as fallback
        chrome_files = self.check_chrome_downloads_folder()
        if chrome_files:
            logger.warning(f"File not found in configured directory, but found {len(chrome_files)} file(s) in Chrome Downloads folder")
            for f in chrome_files:
                logger.info(f"  Found: {f.name} ({f.stat().st_size:,} bytes)")
            # Move file to correct location
            if chrome_files:
                target_file = chrome_files[0]
                try:
                    moved_file = self.output_dir / target_file.name
                    import shutil
                    shutil.move(str(target_file), str(moved_file))
                    logger.info(f"✓ Moved file to correct location: {moved_file.name}")
                    self.downloaded_files.append(moved_file)
                    return True
                except Exception as e:
                    logger.error(f"Failed to move file: {e}")
        
        logger.warning("No new file found in download directory or Chrome Downloads folder")
        return False
    
    def download_resume_from_profile(self, candidate_url: str) -> bool:
        """
        Navigate to a candidate profile and download their resume.
        
        Args:
            candidate_url: URL or reference to candidate profile
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Navigate to candidate profile - ensure we use /profile endpoint
            if isinstance(candidate_url, str) and candidate_url.startswith("http"):
                # Ensure URL ends with /profile
                if not candidate_url.endswith("/profile"):
                    # Replace /scorecard or any other endpoint with /profile
                    candidate_url = re.sub(r'/candidate/(\d+)/.*$', r'/candidate/\1/profile', candidate_url)
                logger.info(f"Opening candidate profile: {candidate_url}")
                self.driver.get(candidate_url)
            else:
                # It's a WebElement, extract ID and construct profile URL
                try:
                    # Try to get candidate ID from element
                    candidate_id = None
                    if hasattr(candidate_url, 'get_attribute'):
                        href = candidate_url.get_attribute("href")
                        if href:
                            import re
                            match = re.search(r'/candidate/(\d+)', href)
                            if match:
                                candidate_id = match.group(1)
                    
                    if candidate_id:
                        profile_url = f"https://app.jazz.co/app/v2/job/{self.job_id}/candidate/{candidate_id}/profile"
                        logger.info(f"Opening candidate profile: {profile_url}")
                        self.driver.get(profile_url)
                    else:
                        logger.info("Clicking candidate row...")
                        candidate_url.click()
                except Exception as e:
                    logger.warning(f"Could not extract candidate ID, clicking element: {e}")
                    candidate_url.click()
            
            # Wait for profile to load
            time.sleep(3)
            
            # Wait for Documents section to appear
            wait = WebDriverWait(self.driver, 30)
            
            try:
                # Look for Documents section - try multiple approaches
                documents_section = None
                
                # Method 1: Look for sidebar block with Documents text
                try:
                    documents_section = wait.until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'jz-sidebar-block') and contains(., 'Documents')]"))
                    )
                except TimeoutException:
                    # Method 2: Look for any sidebar block
                    try:
                        documents_section = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".jz-sidebar-block"))
                        )
                    except TimeoutException:
                        # Method 3: Look for file icon anywhere
                        documents_section = self.driver
                
                # Find resume download element - look for jz-document-card-meta
                file_element = None
                
                # Primary method: Find elements containing "download" text or download-related attributes
                file_element = None
                
                try:
                    # Method 1: Look for links with "download" attribute
                    download_links = documents_section.find_elements(By.CSS_SELECTOR, "a[download]")
                    if download_links:
                        logger.info(f"Found {len(download_links)} link(s) with download attribute")
                        file_element = download_links[0]
                    
                    # Method 2: Look for links containing "download" in href
                    if not file_element:
                        href_download_links = documents_section.find_elements(By.XPATH, ".//a[contains(@href, 'download')]")
                        if href_download_links:
                            logger.info(f"Found {len(href_download_links)} link(s) with 'download' in href")
                            file_element = href_download_links[0]
                    
                    # Method 3: Look for elements containing "download" text (case-insensitive)
                    if not file_element:
                        text_download_elements = documents_section.find_elements(By.XPATH, ".//*[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]")
                        if text_download_elements:
                            logger.info(f"Found {len(text_download_elements)} element(s) containing 'download' text")
                            # Find the closest link ancestor
                            for elem in text_download_elements:
                                try:
                                    file_element = elem.find_element(By.XPATH, "./ancestor::a[1]")
                                    if file_element:
                                        logger.info("Found link ancestor of element with 'download' text")
                                        break
                                except NoSuchElementException:
                                    # Element itself might be clickable
                                    if elem.tag_name == 'a':
                                        file_element = elem
                                        break
                    
                    # Method 4: Look for document card with class jz-document-card-meta jz-horizontal-list
                    # Then find the download link with class jz-document-card-name
                    if not file_element:
                        document_cards = documents_section.find_elements(By.CSS_SELECTOR, ".jz-document-card-meta.jz-horizontal-list")
                        if not document_cards:
                            document_cards = documents_section.find_elements(By.XPATH, ".//*[contains(@class, 'jz-document-card-meta') and contains(@class, 'jz-horizontal-list')]")
                        
                        if document_cards:
                            logger.info(f"Found {len(document_cards)} document card(s) with jz-document-card-meta jz-horizontal-list")
                            card = document_cards[0]
                            
                            # Look for download link within the card
                            try:
                                file_element = card.find_element(By.CSS_SELECTOR, "a.jz-document-card-name")
                                logger.info("Found download link with class jz-document-card-name")
                            except NoSuchElementException:
                                # Look for any link with download attribute or download in href
                                try:
                                    file_element = card.find_element(By.CSS_SELECTOR, "a[download], a[href*='download']")
                                    logger.info("Found download link in card")
                                except NoSuchElementException:
                                    try:
                                        file_element = card.find_element(By.CSS_SELECTOR, "a")
                                        logger.info("Found any link in card")
                                    except NoSuchElementException:
                                        pass
                    
                    # Method 5: Direct search for jz-document-card-name link
                    if not file_element:
                        try:
                            file_element = documents_section.find_element(By.CSS_SELECTOR, "a.jz-document-card-name")
                            logger.info("Found download link with class jz-document-card-name (direct search)")
                        except NoSuchElementException:
                            pass
                    
                except Exception as e:
                    logger.debug(f"Error finding download element: {e}")
                
                # Fallback: Try to find the file icon with class fa fa-file
                if not file_element:
                    try:
                        file_icons = documents_section.find_elements(By.CSS_SELECTOR, "i.fa.fa-file")
                        if file_icons:
                            # Get the parent link element
                            file_element = file_icons[0]
                            # Try to find the clickable parent (usually an <a> tag)
                            try:
                                file_link = file_element.find_element(By.XPATH, "./ancestor::a[1]")
                                file_element = file_link
                            except NoSuchElementException:
                                # Try parent element
                                try:
                                    file_link = file_element.find_element(By.XPATH, "./parent::a")
                                    file_element = file_link
                                except NoSuchElementException:
                                    # Click the icon itself or its parent
                                    pass
                    except Exception as e:
                        logger.debug(f"Could not find .fa.fa-file icon: {e}")
                
                # Last resort: Look for any file link in Documents section
                if not file_element:
                    try:
                        file_links = documents_section.find_elements(By.CSS_SELECTOR, "a[href*='download'], a[href*='file'], a[href*='document']")
                        if file_links:
                            file_element = file_links[0]
                    except Exception as e:
                        logger.debug(f"Could not find file links: {e}")
                
                if file_element:
                    logger.info("Found resume file. Clicking to download...")
                    
                    # Scroll into view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", file_element)
                    time.sleep(1)
                    
                    # Click the file
                    try:
                        file_element.click()
                    except Exception:
                        # Try JavaScript click
                        self.driver.execute_script("arguments[0].click();", file_element)
                    
                    logger.info("Clicked resume file. Waiting for download...")
                    
                    # Extract candidate ID from URL for tracking
                    candidate_id = None
                    if isinstance(candidate_url, str):
                        match = re.search(r'/candidate/(\d+)', candidate_url)
                        if match:
                            candidate_id = match.group(1)
                    
                    # Verify download completed successfully
                    if self.verify_download():
                        self.downloaded_count += 1
                        if candidate_id:
                            self.downloaded_candidate_ids.add(candidate_id)
                        logger.info("✓ Download verified successfully")
                        return True
                    else:
                        logger.warning("✗ Download verification failed - file not found")
                        self.failed_count += 1
                        return False
                else:
                    logger.warning("No resume file found in Documents section")
                    # Log page source snippet for debugging
                    try:
                        sidebar_html = documents_section.get_attribute("outerHTML")[:500]
                        logger.debug(f"Documents section HTML snippet: {sidebar_html}")
                    except:
                        pass
                    self.failed_count += 1
                    return False
                    
            except TimeoutException:
                logger.warning("Documents section not found or did not load in time")
                self.failed_count += 1
                return False
            except Exception as e:
                logger.error(f"Error finding Documents section: {e}")
                self.failed_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Error downloading resume from profile: {e}")
            self.failed_count += 1
            return False
    
    def download_all_resumes(self):
        """Main method to download all resumes for the job."""
        try:
            # Set up browser
            self.setup_driver()
            
            # Navigate to candidate list
            self.navigate_to_candidate_list()
            
            # Get all candidate links (will scroll to end first, then filter out "Not Hired" candidates)
            logger.info("Extracting candidate links (scrolling to load all candidates and filtering 'Not Hired' status)...")
            candidate_links = self.get_candidate_links()
            
            if not candidate_links:
                logger.error("No candidate links found. Please check the page structure.")
                logger.info("Waiting 10 seconds and retrying...")
                time.sleep(10)
                # Try navigating again and getting links
                self.navigate_to_candidate_list()
                candidate_links = self.get_candidate_links()
            
            if not candidate_links:
                logger.error("Still no candidate links found after retry. This may indicate:")
                logger.error("1. The job ID is incorrect")
                logger.error("2. You don't have access to this job")
                logger.error("3. The page structure has changed")
                logger.error("Exiting.")
                return
            
            logger.info(f"Starting download process for {len(candidate_links)} candidates...")
            
            # Download resume for each candidate
            for i, candidate_url in enumerate(candidate_links, 1):
                # Check for cancellation
                if self.cancelled:
                    logger.info("Download cancelled by user")
                    return
                
                logger.info(f"Processing candidate {i}/{len(candidate_links)}")
                
                try:
                    # Download resume
                    success = self.download_resume_from_profile(candidate_url)
                    
                    if success:
                        logger.info(f"✓ Successfully downloaded resume {i}/{len(candidate_links)}")
                    else:
                        logger.warning(f"✗ Failed to download resume {i}/{len(candidate_links)}")
                    
                    # Return to candidate list for next iteration
                    if i < len(candidate_links):
                        self.navigate_to_candidate_list()
                        time.sleep(2)
                    
                    # Add delay to avoid being blocked
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing candidate {i}: {e}")
                    self.failed_count += 1
                    # Try to return to candidate list
                    try:
                        self.navigate_to_candidate_list()
                    except:
                        pass
            
            # Final verification - count actual files and check uniqueness
            final_files = self.get_downloaded_files()
            
            # Check for unique downloads
            unique_candidates_found = len(self.all_candidate_ids)
            unique_candidates_downloaded = len(self.downloaded_candidate_ids)
            missing_candidates = self.all_candidate_ids - self.downloaded_candidate_ids
            
            logger.info("=" * 60)
            logger.info("Download Summary")
            logger.info("=" * 60)
            logger.info(f"Total Candidates Found: {len(candidate_links)} ({unique_candidates_found} unique IDs)")
            logger.info(f"Successfully Downloaded: {self.downloaded_count} ({unique_candidates_downloaded} unique)")
            logger.info(f"Failed: {self.failed_count}")
            logger.info(f"Files in directory: {len(final_files)}")
            logger.info(f"Files saved to: {self.output_dir}")
            
            # Check if all unique resumes are downloaded
            if unique_candidates_found > 0:
                download_percentage = (unique_candidates_downloaded / unique_candidates_found) * 100
                logger.info(f"\nUnique Resume Download Status:")
                logger.info(f"  Downloaded: {unique_candidates_downloaded} / {unique_candidates_found} ({download_percentage:.1f}%)")
                
                if missing_candidates:
                    logger.warning(f"  ⚠ Missing {len(missing_candidates)} unique resume(s)")
                    if len(missing_candidates) <= 20:
                        logger.warning(f"  Missing candidate IDs: {sorted(missing_candidates)}")
                    else:
                        logger.warning(f"  Missing candidate IDs (first 20): {sorted(list(missing_candidates))[:20]}")
                else:
                    logger.info("  ✓ All unique resumes downloaded!")
            
            if final_files:
                total_size = sum(f.stat().st_size for f in final_files)
                logger.info(f"\nTotal size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
                logger.info("\nSample downloaded files:")
                for f in sorted(final_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                    size = f.stat().st_size
                    logger.info(f"  - {f.name} ({size:,} bytes)")
                if len(final_files) > 10:
                    logger.info(f"  ... and {len(final_files) - 10} more files")
            else:
                logger.warning("\n⚠ No files found in download directory!")
                logger.warning("Files may have been downloaded to Chrome's default Downloads folder.")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error in download process: {e}")
            raise
        finally:
            if self.driver:
                logger.info("Closing browser...")
                self.driver.quit()


def main():
    """Main entry point."""
    job_id = input("Enter the job ID (or press Enter for 10545457): ").strip()
    if not job_id:
        job_id = "10545457"
    
    downloader = JazzHRBrowserDownloader(job_id)
    downloader.download_all_resumes()


if __name__ == "__main__":
    main()
