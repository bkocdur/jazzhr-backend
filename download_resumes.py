#!/usr/bin/env python3
"""
JazzHR Resume Downloader

This script connects to the JazzHR API and downloads all resumes for a specified job.
"""

import os
import sys
import time
import logging
import requests
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_resumes.log'),
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
            'User-Agent': 'JazzHR-Resume-Downloader/1.0'
        })
        self.call_times = []
        
    def _rate_limit(self):
        """Enforce rate limiting (80 calls per minute)."""
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
            endpoint: API endpoint (e.g., '/applicants2jobs')
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response as a dictionary
            
        Raises:
            requests.RequestException: If the request fails after all retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        
        for attempt in range(max_retries):
            self._rate_limit()
            
            try:
                logger.debug(f"Making request to {endpoint} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, params=params, timeout=120)  # Increased timeout to 120s
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
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
    
    def _paginate_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Make paginated API requests and collect all results.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            List of all results across all pages
        """
        all_results = []
        page = 1
        
        while True:
            # Add pagination to endpoint
            paginated_endpoint = f"{endpoint}/page/{page}" if page > 1 else endpoint
            
            try:
                response = self._make_request(paginated_endpoint, params)
                
                # Handle different response formats
                if isinstance(response, list):
                    results = response
                elif isinstance(response, dict):
                    # Some endpoints return a dict with a 'data' key
                    if 'data' in response:
                        results = response['data']
                    else:
                        # If it's a single object, wrap it in a list
                        results = [response] if response else []
                else:
                    results = []
                
                if not results:
                    break
                    
                all_results.extend(results)
                logger.info(f"Retrieved page {page}: {len(results)} items (total: {len(all_results)})")
                
                # If we got fewer than 100 results, we've reached the last page
                if len(results) < 100:
                    break
                    
                page += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
        
        return all_results
    
    def get_applicants_for_job(self, job_id: str) -> List[Dict]:
        """
        Get all applicants for a specific job.
        
        Args:
            job_id: The job ID
            
        Returns:
            List of applicant-job mappings
        """
        logger.info(f"Fetching applicants for job ID: {job_id}")
        params = {'job_id': job_id}
        return self._paginate_request('/applicants2jobs', params)
    
    def get_applicant_details(self, applicant_id: str) -> Dict:
        """
        Get detailed information about a specific applicant.
        
        Args:
            applicant_id: The applicant ID
            
        Returns:
            Applicant details dictionary
        """
        logger.debug(f"Fetching details for applicant ID: {applicant_id}")
        return self._make_request(f'/applicants/{applicant_id}')
    
    def get_files_for_applicant(self, applicant_id: str) -> List[Dict]:
        """
        Get all files for a specific applicant.
        
        Args:
            applicant_id: The applicant ID
            
        Returns:
            List of file metadata dictionaries
        """
        logger.debug(f"Fetching files for applicant ID: {applicant_id}")
        params = {'applicant_id': applicant_id}
        return self._paginate_request('/files', params)
    
    def get_file_details(self, file_id: str) -> Dict:
        """
        Get detailed information about a specific file.
        
        Args:
            file_id: The file ID
            
        Returns:
            File details dictionary
        """
        logger.debug(f"Fetching details for file ID: {file_id}")
        return self._make_request(f'/files/{file_id}')
    
    def get_all_jobs(self, status: Optional[str] = None) -> List[Dict]:
        """
        Get all jobs from the API.
        
        Args:
            status: Optional job status filter (e.g., 'open', 'closed')
            
        Returns:
            List of job dictionaries
        """
        logger.debug("Fetching all jobs from API")
        params = {}
        if status:
            params['status'] = status
        return self._paginate_request('/jobs', params)
    
class ResumeDownloader:
    """Handles downloading resumes from JazzHR."""
    
    def __init__(self, api: JazzHRAPI, output_dir: str = "resumes"):
        """
        Initialize the resume downloader.
        
        Args:
            api: JazzHR API client instance
            output_dir: Base directory for downloaded resumes
        """
        self.api = api
        self.output_dir = Path(output_dir)
        self.downloaded_count = 0
        self.failed_count = 0
        
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
    
    def get_file_extension(self, file_data: Dict) -> str:
        """
        Determine file extension from file metadata.
        
        Args:
            file_data: File metadata dictionary
            
        Returns:
            File extension (e.g., '.pdf')
        """
        # Try to get extension from filename
        filename = file_data.get('filename', '')
        if filename:
            ext = Path(filename).suffix
            if ext:
                return ext
        
        # Try to get extension from file type
        file_type = file_data.get('file_type', '').lower()
        if 'pdf' in file_type:
            return '.pdf'
        elif 'doc' in file_type or 'word' in file_type:
            return '.doc'
        elif 'docx' in file_type:
            return '.docx'
        elif 'txt' in file_type:
            return '.txt'
        
        # Default to .pdf for resumes
        return '.pdf'
    
    def download_file(self, file_data: Dict, applicant_data: Dict, job_id: str) -> bool:
        """
        Download a file from JazzHR.
        
        Args:
            file_data: File metadata dictionary
            applicant_data: Applicant metadata dictionary
            job_id: Job ID for organizing files
            
        Returns:
            True if download successful, False otherwise
        """
        file_id = file_data.get('id') or file_data.get('file_id')
        if not file_id:
            logger.warning(f"No file ID found in file data: {file_data}")
            return False
        
        # Try to get file details which might contain download URL
        try:
            file_details = self.api.get_file_details(file_id)
            file_data.update(file_details)
        except Exception as e:
            logger.warning(f"Could not fetch file details for {file_id}: {e}")
        
        # Check for download URL in file data
        download_url = (
            file_data.get('url') or 
            file_data.get('download_url') or 
            file_data.get('file_url') or
            file_data.get('link')
        )
        
        if not download_url:
            logger.warning(f"No download URL found for file {file_id}. File data: {file_data}")
            logger.info("Note: JazzHR API may not provide direct file download URLs.")
            logger.info("You may need to download files manually from the JazzHR UI.")
            return False
        
        # Get applicant name for filename
        applicant_name = "Unknown"
        if applicant_data:
            first_name = applicant_data.get('first_name', '')
            last_name = applicant_data.get('last_name', '')
            if first_name or last_name:
                applicant_name = f"{first_name}_{last_name}".strip('_')
            else:
                applicant_name = applicant_data.get('email', 'Unknown')
        
        # Create output directory
        job_dir = self.output_dir / f"job_{job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        file_ext = self.get_file_extension(file_data)
        
        # Create filename
        filename = self.sanitize_filename(f"{applicant_name}_{file_id}{file_ext}")
        filepath = job_dir / filename
        
        # Download the file
        try:
            logger.info(f"Downloading file {file_id} for {applicant_name}...")
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()
            
            # Save file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Successfully downloaded: {filepath}")
            self.downloaded_count += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            self.failed_count += 1
            return False
    
    def download_resumes_for_job(self, job_id: str) -> Dict:
        """
        Download all resumes for a specific job.
        
        Args:
            job_id: The job ID
            
        Returns:
            Dictionary with download statistics
        """
        logger.info(f"Starting resume download for job ID: {job_id}")
        
        # Get all applicants for the job
        applicant_job_mappings = self.api.get_applicants_for_job(job_id)
        
        if not applicant_job_mappings:
            logger.warning(f"No applicants found for job {job_id}")
            return {
                'total_applicants': 0,
                'downloaded': 0,
                'failed': 0
            }
        
        logger.info(f"Found {len(applicant_job_mappings)} applicant(s) for job {job_id}")
        
        # Process each applicant
        for mapping in applicant_job_mappings:
            applicant_id = mapping.get('applicant_id') or mapping.get('id')
            if not applicant_id:
                logger.warning(f"No applicant_id found in mapping: {mapping}")
                continue
            
            # Get applicant details
            try:
                applicant_data = self.api.get_applicant_details(applicant_id)
            except Exception as e:
                logger.error(f"Failed to get applicant details for {applicant_id}: {e}")
                applicant_data = {}
            
            # Get files for this applicant
            files = self.api.get_files_for_applicant(applicant_id)
            
            if not files:
                logger.info(f"No files found for applicant {applicant_id}")
                continue
            
            logger.info(f"Found {len(files)} file(s) for applicant {applicant_id}")
            
            # Download each file
            for file_data in files:
                self.download_file(file_data, applicant_data, job_id)
        
        stats = {
            'total_applicants': len(applicant_job_mappings),
            'downloaded': self.downloaded_count,
            'failed': self.failed_count
        }
        
        logger.info(f"Download complete. Downloaded: {stats['downloaded']}, Failed: {stats['failed']}")
        return stats


def main():
    """Main entry point."""
    # Get API key from environment or use default
    api_key = os.getenv('JAZZHR_API_KEY', 'ZNvLmHc2BfuKI0XfZjhAiOnk7CleAC67')
    
    if not api_key:
        logger.error("API key not found. Please set JAZZHR_API_KEY environment variable.")
        sys.exit(1)
    
    # Get job ID from user
    job_id = input("Enter the job ID: ").strip()
    
    if not job_id:
        logger.error("Job ID is required.")
        sys.exit(1)
    
    # Initialize API client and downloader
    api = JazzHRAPI(api_key)
    downloader = ResumeDownloader(api)
    
    # Download resumes
    stats = downloader.download_resumes_for_job(job_id)
    
    # Print summary
    print("\n" + "="*50)
    print("Download Summary")
    print("="*50)
    print(f"Total Applicants: {stats['total_applicants']}")
    print(f"Files Downloaded: {stats['downloaded']}")
    print(f"Files Failed: {stats['failed']}")
    print("="*50)


if __name__ == "__main__":
    main()
