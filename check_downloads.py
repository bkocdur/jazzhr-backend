#!/usr/bin/env python3
"""
Check download status for JazzHR resumes.
"""

import sys
from pathlib import Path

def check_downloads(job_id: str = "10545457"):
    """Check download status for a specific job."""
    download_dir = Path("resumes") / f"job_{job_id}"
    
    print("=" * 60)
    print(f"Download Status for Job ID: {job_id}")
    print("=" * 60)
    
    if not download_dir.exists():
        print(f"❌ Download directory does not exist: {download_dir}")
        print("   No downloads have been completed yet.")
        return
    
    files = [f for f in download_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    if not files:
        print(f"⚠️  Download directory exists but is empty: {download_dir}")
        print("   Files may have been downloaded to Chrome's default Downloads folder.")
        
        # Check Downloads folder
        downloads_dir = Path.home() / "Downloads"
        if downloads_dir.exists():
            pdf_files = list(downloads_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\n   Found {len(pdf_files)} PDF file(s) in Downloads folder:")
                for f in sorted(pdf_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                    size = f.stat().st_size
                    mtime = f.stat().st_mtime
                    from datetime import datetime
                    print(f"     - {f.name} ({size:,} bytes, {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')})")
        return
    
    print(f"✓ Download directory: {download_dir}")
    print(f"✓ Total files: {len(files)}")
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in files)
    print(f"✓ Total size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    
    # Show file details
    print("\nDownloaded files:")
    print("-" * 60)
    
    # Sort by modification time (newest first)
    sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    for i, f in enumerate(sorted_files[:20], 1):
        size = f.stat().st_size
        mtime = f.stat().st_mtime
        from datetime import datetime
        print(f"{i:3d}. {f.name}")
        print(f"     Size: {size:,} bytes | Modified: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    if len(sorted_files) > 20:
        print(f"\n... and {len(sorted_files) - 20} more files")
    
    # Check for empty files
    empty_files = [f for f in files if f.stat().st_size == 0]
    if empty_files:
        print(f"\n⚠️  Warning: {len(empty_files)} empty file(s) found:")
        for f in empty_files:
            print(f"     - {f.name}")
    
    print("=" * 60)

if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else "10545457"
    check_downloads(job_id)
