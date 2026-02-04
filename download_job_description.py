#!/usr/bin/env python3
"""
JazzHR Job Description Downloader

This script downloads job descriptions from JazzHR API for a specific job ID.
"""

import os
import sys
import logging
import requests
import html
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_job_description.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class JazzHRAPI:
    """Client for interacting with the JazzHR API."""
    
    BASE_URL = "https://api.resumatorapi.com/v1"
    RATE_LIMIT_CALLS = 80
    RATE_LIMIT_WINDOW = 60  # seconds
    
    def __init__(self, api_key: str):
        """
        Initialize the JazzHR API client.
        
        Args:
            api_key: The JazzHR API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'JazzHR-Job-Description-Downloader/1.0'
        })
        self.call_times = []
        
    def _rate_limit(self):
        """Enforce rate limiting (80 calls per minute)."""
        import time
        now = time.time()
        # Remove calls older than the rate limit window
        self.call_times = [t for t in self.call_times if now - t < self.RATE_LIMIT_WINDOW]
        
        # If we've hit the limit, wait
        if len(self.call_times) >= self.RATE_LIMIT_CALLS:
            sleep_time = self.RATE_LIMIT_WINDOW - (now - self.call_times[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Waiting {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                # Clean up old calls after waiting
                self.call_times = [t for t in self.call_times if time.time() - t < self.RATE_LIMIT_WINDOW]
        
        # Record this call
        self.call_times.append(time.time())
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        Make an API request with rate limiting, retries, and error handling.
        
        Args:
            endpoint: API endpoint (e.g., '/jobs')
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response as a dictionary
            
        Raises:
            requests.RequestException: If the request fails after all retries
        """
        import time
        url = f"{self.BASE_URL}{endpoint}"
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        for attempt in range(max_retries):
            self._rate_limit()
            
            try:
                logger.debug(f"Making request to {endpoint} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, params=params, timeout=120)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request timeout for {endpoint}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API request failed for {endpoint} after {max_retries} attempts: {e}")
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed for {endpoint}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API request failed for {endpoint} after {max_retries} attempts: {e}")
                    raise
    
    def get_open_jobs(self) -> list:
        """
        Get all open jobs from the API (with pagination support).
        
        Returns:
            List of job dictionaries
        """
        logger.info("Fetching all open jobs from API...")
        all_jobs = []
        page = 1
        
        try:
            while True:
                print(f"Fetching page {page}... (found {len(all_jobs)} jobs so far)", end='\r')
                logger.debug(f"Fetching page {page} of open jobs...")
                jobs = self._make_request('/jobs', {'status': 'open', 'page': page})
                
                # Handle response format
                page_jobs = []
                if isinstance(jobs, list):
                    page_jobs = jobs
                elif isinstance(jobs, dict) and 'data' in jobs:
                    page_jobs = jobs['data']
                elif jobs:
                    page_jobs = [jobs]
                
                if not page_jobs:
                    break
                
                all_jobs.extend(page_jobs)
                
                # JazzHR API typically returns 100 results per page
                # If we got fewer than 100, we've reached the last page
                if len(page_jobs) < 100:
                    break
                
                page += 1
            
            print()  # New line after progress updates
            
            logger.info(f"Fetched {len(all_jobs)} open job(s) across {page} page(s)")
            return all_jobs
        except Exception as e:
            logger.error(f"Error fetching open jobs: {e}")
            return all_jobs  # Return what we've collected so far
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """
        Get job details including description for a specific job ID.
        Uses applicants2jobs to get the API job ID, then fetches job details.
        
        Args:
            job_id: The numeric job ID from web interface (e.g., '10545457')
            
        Returns:
            Job dictionary with description and metadata, None if not found
        """
        logger.info(f"Fetching job details for job ID: {job_id}")
        
        # Use applicants2jobs to get API job ID (most direct approach)
        try:
            logger.info("Querying applicants2jobs to get API job ID...")
            applicants2jobs = self._make_request('/applicants2jobs', {'job_id': job_id})
            
            # Handle response format (could be list or dict)
            if isinstance(applicants2jobs, list):
                mappings = applicants2jobs
            elif isinstance(applicants2jobs, dict) and 'data' in applicants2jobs:
                mappings = applicants2jobs['data']
            else:
                mappings = [applicants2jobs] if applicants2jobs else []
            
            if mappings and len(mappings) > 0:
                # Get API job ID from first mapping
                api_job_id = mappings[0].get('job_id')
                if api_job_id:
                    logger.info(f"Found API job ID: {api_job_id}")
                    try:
                        job_data = self._make_request(f'/jobs/{api_job_id}')
                        if job_data and isinstance(job_data, dict) and 'id' in job_data:
                            logger.info(f"✓ Successfully retrieved job: {job_data.get('title', 'Unknown')}")
                            return job_data
                    except Exception as e:
                        logger.error(f"Could not fetch job with API ID {api_job_id}: {e}")
                else:
                    logger.warning("No job_id field found in applicants2jobs response")
                    logger.debug(f"Sample mapping: {mappings[0]}")
            else:
                logger.warning(f"No applicants2jobs mappings found for job ID: {job_id}")
        except Exception as e:
            logger.error(f"Error querying applicants2jobs: {e}")
        
        # Fallback: Try direct API call with numeric ID
        try:
            job_data = self._make_request(f'/jobs/{job_id}')
            if job_data and isinstance(job_data, dict) and 'id' in job_data:
                logger.info(f"Found job directly with numeric ID: {job_id}")
                return job_data
        except Exception as e:
            logger.debug(f"Direct lookup failed: {e}")
        
        logger.error(f"Could not find job with ID: {job_id}")
        return None


class JobDescriptionDownloader:
    """Handles downloading job descriptions from JazzHR."""
    
    def __init__(self, api: JazzHRAPI, output_dir: str = "job_descriptions"):
        """
        Initialize the job description downloader.
        
        Args:
            api: JazzHR API client instance
            output_dir: Base directory for downloaded job descriptions
        """
        self.api = api
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to remove invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        return filename
    
    def html_to_text(self, html_content: str) -> str:
        """
        Convert HTML content to plain text.
        
        Args:
            html_content: HTML string
            
        Returns:
            Plain text string
        """
        if not html_content:
            return ""
        
        # Decode HTML entities
        text = html.unescape(html_content)
        
        # Remove HTML tags using regex
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def save_job_description(self, job_data: Dict, job_id: str, format: str = 'html') -> bool:
        """
        Save job description to file.
        
        Args:
            job_data: Job dictionary from API
            job_id: Job ID for file naming
            format: File format ('html' or 'txt')
            
        Returns:
            True if saved successfully, False otherwise
        """
        if not job_data:
            logger.warning("No job data provided")
            return False
        
        description = job_data.get('description', '')
        if not description:
            logger.warning("No description field found in job data")
            return False
        
        # Prepare filename
        job_title = job_data.get('title', 'Unknown_Job')
        job_title = self.sanitize_filename(job_title)
        
        if format.lower() == 'txt':
            # Convert HTML to text
            text_content = self.html_to_text(description)
            filename = f"{job_id}_{job_title}_job_description.txt"
            filepath = self.output_dir / filename
            
            # Create text file with metadata header
            content = f"Job Description: {job_data.get('title', 'N/A')}\n"
            content += f"Job ID: {job_id}\n"
            content += f"Department: {job_data.get('department', 'N/A')}\n"
            content += f"Location: {job_data.get('city', '')}, {job_data.get('state', '')} {job_data.get('zip', '')}\n"
            content += f"Country: {job_data.get('country_id', 'N/A')}\n"
            content += f"Date Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += "\n" + "="*60 + "\n\n"
            content += text_content
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✓ Saved job description as text: {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to save job description: {e}")
                return False
        else:
            # Save as HTML
            filename = f"{job_id}_{job_title}_job_description.html"
            filepath = self.output_dir / filename
            
            # Create HTML file with metadata
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Job Description: {html.escape(job_data.get('title', 'N/A'))}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .metadata {{ background-color: #f5f5f5; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
        .metadata h2 {{ margin-top: 0; }}
        .metadata p {{ margin: 5px 0; }}
        .description {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="metadata">
        <h2>Job Information</h2>
        <p><strong>Title:</strong> {html.escape(job_data.get('title', 'N/A'))}</p>
        <p><strong>Job ID:</strong> {html.escape(str(job_id))}</p>
        <p><strong>Department:</strong> {html.escape(job_data.get('department', 'N/A'))}</p>
        <p><strong>Location:</strong> {html.escape(f"{job_data.get('city', '')}, {job_data.get('state', '')} {job_data.get('zip', '')}".strip(', '))}</p>
        <p><strong>Country:</strong> {html.escape(job_data.get('country_id', 'N/A'))}</p>
        <p><strong>Date Extracted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="description">
        <h2>Job Description</h2>
        {description}
    </div>
</body>
</html>"""
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"✓ Saved job description as HTML: {filepath}")
                return True
            except Exception as e:
                logger.error(f"Failed to save job description: {e}")
                return False
    
    def download_job_description(self, job_id: str, format: str = 'html') -> bool:
        """
        Download job description for a specific job.
        
        Args:
            job_id: The job ID
            format: File format ('html' or 'txt')
            
        Returns:
            True if download successful, False otherwise
        """
        logger.info(f"Downloading job description for job ID: {job_id}")
        
        try:
            # Get job details from API
            job_data = self.api.get_job_details(job_id)
            
            if not job_data:
                logger.error(f"Could not retrieve job details for job ID: {job_id}")
                return False
            
            # Save job description
            success = self.save_job_description(job_data, job_id, format)
            
            if success:
                logger.info(f"✓ Successfully downloaded job description for job ID: {job_id}")
            else:
                logger.error(f"✗ Failed to save job description for job ID: {job_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error downloading job description: {e}")
            return False


def list_open_jobs(api: JazzHRAPI) -> None:
    """List all open jobs."""
    print("\nFetching open jobs...")
    jobs = api.get_open_jobs()
    
    if not jobs:
        print("No open jobs found.")
        return
    
    print(f"\n{'='*120}")
    print(f"Found {len(jobs)} open job(s):")
    print(f"{'='*120}")
    print(f"{'#':<5} {'Job ID':<30} {'Title':<35} {'Hiring Lead':<25} {'Open Date':<15}")
    print(f"{'-'*120}")
    
    for i, job in enumerate(jobs, 1):
        job_api_id = job.get('id', 'N/A')
        title = job.get('title', 'N/A')
        hiring_lead = job.get('hiring_lead', 'N/A')
        from_open_date = job.get('from_open_date', 'N/A')
        
        # Truncate long values
        if len(title) > 32:
            title = title[:32] + "..."
        if len(hiring_lead) > 22:
            hiring_lead = hiring_lead[:22] + "..."
        if len(str(from_open_date)) > 12:
            from_open_date = str(from_open_date)[:12]
        
        print(f"{i:<5} {job_api_id:<30} {title:<35} {hiring_lead:<25} {from_open_date:<15}")
    
    print(f"{'='*120}\n")


def main():
    """Main entry point."""
    # Get API key from environment or use default
    api_key = os.getenv('JAZZHR_API_KEY', 'ZNvLmHc2BfuKI0XfZjhAiOnk7CleAC67')
    
    if not api_key:
        logger.error("API key not found. Please set JAZZHR_API_KEY environment variable.")
        sys.exit(1)
    
    # Initialize API client
    api = JazzHRAPI(api_key)
    
    # Ask user what they want to do
    print("\n" + "="*60)
    print("JazzHR Job Description Downloader")
    print("="*60)
    print("1. List all open jobs")
    print("2. Download job description by ID")
    print("="*60)
    
    choice = input("Choose an option (1 or 2): ").strip()
    
    if choice == '1':
        # List open jobs
        list_open_jobs(api)
        
        # Ask if they want to download a job description
        download_choice = input("\nDownload a job description? (y/n): ").strip().lower()
        if download_choice == 'y':
            job_id = input("Enter the job ID (numeric or API format): ").strip()
            if not job_id:
                print("Job ID is required.")
                sys.exit(1)
        else:
            sys.exit(0)
    elif choice == '2':
        # Get job ID from user
        job_id = input("Enter the job ID (numeric or API format): ").strip()
        if not job_id:
            logger.error("Job ID is required.")
            sys.exit(1)
    else:
        logger.error("Invalid choice.")
        sys.exit(1)
    
    # Ask for format
    format_choice = input("Save as HTML or TXT? (html/txt, default: html): ").strip().lower()
    if format_choice not in ['html', 'txt']:
        format_choice = 'html'
    
    # Initialize downloader
    downloader = JobDescriptionDownloader(api)
    
    # Download job description
    success = downloader.download_job_description(job_id, format=format_choice)
    
    # Print summary
    print("\n" + "="*50)
    if success:
        print("✓ Job description downloaded successfully!")
        print(f"File saved to: {downloader.output_dir}")
    else:
        print("✗ Failed to download job description")
    print("="*50)


if __name__ == "__main__":
    main()
