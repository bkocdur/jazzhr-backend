# JazzHR Resume Downloader

Two Python scripts to download all resumes for a specific job from JazzHR:
1. **API Method** (`download_resumes.py`) - Uses JazzHR API (limited - files may not be downloadable)
2. **Browser Automation Method** (`download_resumes_browser.py`) - Uses Selenium to automate the web interface (recommended)

## Features

- Connects to JazzHR API using your API key
- Retrieves all applicants for a specified job ID
- Downloads all resume files associated with those applicants
- Handles pagination automatically (supports 100+ applicants)
- Implements rate limiting (respects 80 calls/minute limit)
- Organizes downloads by job ID
- Comprehensive logging of all operations

## Prerequisites

- Python 3.7 or higher
- Chrome browser installed (for browser automation method)
- A JazzHR account with access to the job
- (Optional) A JazzHR API key (found in Settings > Integrations in your JazzHR account)

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API key (optional - defaults to provided key):
   - Create a `.env` file in the project directory
   - Add: `JAZZHR_API_KEY=your_api_key_here`
   - Or the script will use the default API key provided

## Usage

### Browser Automation Method (Recommended)

This method uses Selenium to automate the JazzHR web interface and download resumes directly:

```bash
python download_resumes_browser.py
```

When prompted, enter the job ID (or press Enter for default: 10545457).

**The script will:**
1. Open Chrome browser and navigate to the candidate list page
2. **If login is required**: The script will pause and ask you to log in manually, then press Enter to continue
3. Extract all candidate profile links from the page
4. For each candidate:
   - Open their profile
   - Find the Documents section in the sidebar
   - Click on the resume file (icon with class `fa fa-file`)
   - Download the file
   - Return to candidate list
5. Save all files to `resumes/job_{job_id}/` directory

**Note**: The browser window will be visible so you can monitor progress and log in if needed.

### API Method (Limited)

Run the API script:
```bash
python download_resumes.py
```

**Note**: This method has limitations - JazzHR API does not provide direct file download URLs, so downloads may fail.

## Output

- **Downloaded files**: Saved in `resumes/job_{job_id}/` directory
- **Log files**: 
  - `download_resumes_browser.log` - Browser automation logs
  - `download_resumes.log` - API method logs
- **Console output**: Progress updates and summary statistics

## Browser Automation Details

### How It Works

1. **Navigation**: Opens Chrome and navigates to `https://app.jazz.co/app/v2/job/{job_id}/candidate`
2. **Login Detection**: Automatically detects if login is required and pauses for manual login
3. **Candidate Extraction**: Finds all candidate profile links on the page
4. **Resume Download**: For each candidate:
   - Opens their profile page
   - Locates the Documents section (`.jz-sidebar-block`)
   - Finds the resume file icon (`.fa.fa-file`)
   - Clicks to download the file
5. **File Management**: Files are automatically saved to the configured download directory

### Requirements

- Chrome browser must be installed
- ChromeDriver will be automatically downloaded by `webdriver-manager`
- Internet connection required

### Troubleshooting Browser Automation

**Chrome not found:**
- Ensure Chrome browser is installed
- On macOS: Chrome should be in `/Applications/Google Chrome.app`
- On Linux: Install Chrome via package manager
- On Windows: Chrome should be in default location

**Login issues:**
- If login is required, the script will pause
- Log in manually in the browser window
- Press Enter in the terminal to continue
- If login fails, check your credentials

**No candidates found:**
- Verify you have access to the job
- Check that the job ID is correct
- The script will pause for inspection if no candidates are found

**Downloads not working:**
- Check that the Documents section is visible on candidate profiles
- Verify you have permission to download files
- Check the log file for specific errors

## API Limitations

**Important**: According to the JazzHR API documentation, resume files cannot be directly extracted via the API and must be downloaded manually from the UI. However, this script attempts to:

1. Retrieve file metadata using the `/files` endpoint
2. Extract download URLs from file metadata if available
3. Download files if URLs are provided

If the API does not provide download URLs, the script will:
- Log a warning for each file that cannot be downloaded
- Provide instructions for manual download
- Still collect all file metadata for reference

## Rate Limiting

The script automatically handles JazzHR's rate limit of 80 API calls per minute. If the limit is reached, the script will wait before making additional requests.

## Error Handling

The script includes comprehensive error handling:
- Network errors are logged and the script continues
- Missing data is handled gracefully
- Failed downloads are tracked and reported
- All errors are logged to both console and log file

## File Organization

Files are organized as follows:
```
resumes/
  └── job_{job_id}/
      ├── John_Doe_file123.pdf
      ├── Jane_Smith_file456.pdf
      └── ...
```

## Troubleshooting

### No files downloaded
- Check the log file (`download_resumes.log`) for detailed error messages
- Verify your API key is correct
- Ensure the job ID exists and has applicants
- Note: If JazzHR API doesn't provide download URLs, manual download may be required

### Rate limit errors
- The script handles rate limiting automatically
- If you see rate limit warnings, the script will wait and retry

### Missing applicants
- Verify the job ID is correct
- Check that the job has applicants associated with it
- Review the log file for API errors

## API Endpoints Used

- `GET /applicants2jobs?job_id={job_id}` - Get applicants for a job
- `GET /applicants/{applicant_id}` - Get applicant details
- `GET /files?applicant_id={applicant_id}` - Get files for an applicant
- `GET /files/{file_id}` - Get file details (may contain download URL)

## License

This script is provided as-is for use with JazzHR API.

## Support

For issues with:
- **This script**: Check the log file and error messages
- **JazzHR API**: Contact JazzHR support at https://help.jazzhr.com/s/contactsupport
