#!/usr/bin/env python3
"""
Enhanced YouTube Downloader Streamlit App
Professional, scalable, and error-resistant UI for downloading YouTube videos using yt-dlp
"""

import streamlit as st
import os
import sys
import yt_dlp
import tempfile
import shutil
from pathlib import Path
import time
import json
from io import BytesIO
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import traceback
from typing import Optional, Dict, List, Any, Tuple
import re
from urllib.parse import urlparse, parse_qs
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="YouTube Downloader Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme configuration
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #1e1e1e !important;
            color: #a8a19f !important;
        }
        .stApp {
            background-color: #1e1e1e;
            color: #a8a19f;
        }
        .css-18e3th9 {
            background-color: #1e1e1e;
            color: #a8a19f;
        }
        .css-1d391kg {
            background-color: #1e1e1e;
            color: #a8a19f;
        }
    </style>
""", unsafe_allow_html=True)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .video-info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }
    
    .download-section {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border: 1px solid #e1e5e9;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .error-message {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .format-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .format-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        border-color: #667eea;
        transform: translateY(-2px);
    }
    
    .progress-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid #e9ecef;
    }
    
    .quick-action-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.2rem;
        transition: all 0.3s ease;
    }
    
    .quick-action-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
</style>
""", unsafe_allow_html=True)

class EnhancedYouTubeDownloader:
    """Enhanced YouTube downloader with better error handling and scalability"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="yt_downloader_")
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Download state tracking
        self.download_state = {
            'status': 'idle',
            'progress': 0,
            'speed': '',
            'eta': '',
            'error': None,
            'total_bytes': 0,
            'downloaded_bytes': 0
        }
        
        # Rate limiting and retry configuration
        self.retry_config = {
            'max_retries': 3,
            'retry_delay': 2,
            'backoff_multiplier': 2
        }
        
    def __del__(self):
        """Cleanup temporary directory"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def is_valid_youtube_url(self, url: str) -> bool:
        """Validate YouTube URL"""
        if not url:
            return False
        
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+'
        ]
        
        return any(re.match(pattern, url) for pattern in youtube_patterns)
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:v/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, url: str, timeout: int = 30) -> Optional[Dict]:
        """Get video information with timeout and error handling"""
        if not self.is_valid_youtube_url(url):
            raise ValueError("Invalid YouTube URL")
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': timeout,
                'extract_flat': False,
                'ignoreerrors': False,
                # Disable subtitle extraction during info gathering to avoid 429 errors
                'writesubtitles': False,
                'writeautomaticsub': False,
                # Add user agent to avoid blocking
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Clean and validate info
                if info:
                    # Remove sensitive or unnecessary data
                    cleaned_info = {
                        'id': info.get('id'),
                        'title': info.get('title', 'Unknown Title'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'duration': info.get('duration'),
                        'view_count': info.get('view_count'),
                        'upload_date': info.get('upload_date'),
                        'description': info.get('description', '')[:500] + '...' if info.get('description', '') else '',
                        'thumbnail': info.get('thumbnail'),
                        'formats': info.get('formats', []),
                        'webpage_url': info.get('webpage_url'),
                        'age_limit': info.get('age_limit', 0),
                        'availability': info.get('availability')
                    }
                    return cleaned_info
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            if 'private' in error_msg or 'unavailable' in error_msg:
                raise ValueError("Video is private or unavailable")
            elif 'copyright' in error_msg:
                raise ValueError("Video is copyright protected")
            elif 'geo' in error_msg or 'blocked' in error_msg:
                raise ValueError("Video is geo-blocked in your region")
            else:
                raise ValueError(f"Download error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise ValueError(f"Failed to get video info: {str(e)}")
        
        return None
    
    def format_duration(self, seconds: Optional[int]) -> str:
        """Format duration from seconds to readable format"""
        if not seconds:
            return "N/A"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def format_filesize(self, size: Optional[int]) -> str:
        """Format file size in human readable format"""
        if not size:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def format_number(self, num: Optional[int]) -> str:
        """Format large numbers with commas"""
        if num is None:
            return "N/A"
        return f"{num:,}"
    
    def get_available_formats(self, info: Dict) -> Tuple[List, List, List]:
        """Get and categorize available formats"""
        formats = info.get('formats', [])
        
        video_formats = []
        audio_formats = []
        combined_formats = []
        
        for fmt in formats:
            # Skip live streams and unavailable formats
            if fmt.get('protocol') in ['m3u8', 'm3u8_native', 'http_dash_segments']:
                continue
                
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            
            if vcodec != 'none' and acodec != 'none':
                combined_formats.append(fmt)
            elif vcodec != 'none' and acodec == 'none':
                video_formats.append(fmt)
            elif acodec != 'none' and vcodec == 'none':
                audio_formats.append(fmt)
        
        # Sort by quality (height for video, abr for audio)
        video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        audio_formats.sort(key=lambda x: x.get('abr', 0), reverse=True)
        combined_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        
        return video_formats[:15], audio_formats[:10], combined_formats[:15]
    
    def build_ydl_opts(self, url: str, download_config: Dict) -> Dict:
        """Build optimized yt-dlp options"""
        video_id = self.extract_video_id(url) or "unknown"
        filename_template = f"{self.temp_dir}/%(title)s.%(ext)s"
        
        base_opts = {
            'outtmpl': filename_template,
            'restrictfilenames': True,
            'windowsfilenames': True,  # Ensure Windows compatibility
            'ignoreerrors': False,
            'no_warnings': False,
            'extract_flat': False,
            
            # Network settings
            'socket_timeout': 30,
            'retries': self.retry_config['max_retries'],
            'fragment_retries': self.retry_config['max_retries'],
            'retry_sleep_functions': {
                'http': lambda n: min(self.retry_config['retry_delay'] * (self.retry_config['backoff_multiplier'] ** n), 60),
                'fragment': lambda n: min(self.retry_config['retry_delay'] * (self.retry_config['backoff_multiplier'] ** n), 60)
            },
            
            # User agent to avoid blocking
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            
            # Avoid subtitle issues that cause 429 errors
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        download_type = download_config.get('type', 'best')
        quality = download_config.get('quality', 'best')
        output_format = download_config.get('format', 'mp4')
        
        # Format selection logic
        if download_type == "video_audio":
            format_selectors = {
                'best': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '2160p': 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '1440p': 'bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]',
                '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]',
                '360p': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]',
                'worst': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worstvideo+worstaudio/worst'
            }
            base_opts['format'] = format_selectors.get(quality, format_selectors['best'])
            
            # Set merge format
            if output_format.lower() in ['mp4', 'mkv', 'webm', 'avi']:
                base_opts['merge_output_format'] = output_format.lower()
                
        elif download_type == "video_only":
            format_selectors = {
                'best': 'bestvideo[height<=2160][ext=mp4]/bestvideo[height<=2160]/bestvideo',
                '2160p': 'bestvideo[height<=2160][ext=mp4]/bestvideo[height<=2160]',
                '1440p': 'bestvideo[height<=1440][ext=mp4]/bestvideo[height<=1440]',
                '1080p': 'bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]',
                '720p': 'bestvideo[height<=720][ext=mp4]/bestvideo[height<=720]',
                '480p': 'bestvideo[height<=480][ext=mp4]/bestvideo[height<=480]',
                '360p': 'bestvideo[height<=360][ext=mp4]/bestvideo[height<=360]',
                'worst': 'worstvideo[ext=mp4]/worstvideo'
            }
            base_opts['format'] = format_selectors.get(quality, format_selectors['best'])
            
        elif download_type == "audio_only":
            quality_map = {
                'best': 'bestaudio[ext=m4a]/bestaudio',
                '320k': 'bestaudio[abr<=320][ext=m4a]/bestaudio[abr<=320]',
                '256k': 'bestaudio[abr<=256][ext=m4a]/bestaudio[abr<=256]',
                '192k': 'bestaudio[abr<=192][ext=m4a]/bestaudio[abr<=192]',
                '128k': 'bestaudio[abr<=128][ext=m4a]/bestaudio[abr<=128]',
                '96k': 'bestaudio[abr<=96][ext=m4a]/bestaudio[abr<=96]'
            }
            base_opts['format'] = quality_map.get(quality, quality_map['best'])
            
            # Audio conversion
            if output_format.lower() in ['mp3', 'aac', 'flac', 'wav', 'ogg']:
                base_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': output_format.lower(),
                    'preferredquality': quality.replace('k', '') if 'k' in quality else '192',
                }]
        
        else:  # fallback
            base_opts['format'] = 'best[ext=mp4]/best'
        
        # Additional options
        additional = download_config.get('additional', {})
        if additional.get('thumbnail'):
            base_opts['writethumbnail'] = True
        
        if additional.get('description'):
            base_opts['writedescription'] = True
        
        # Only enable subtitles if specifically requested and warn about potential issues
        if additional.get('subtitles'):
            base_opts['writesubtitles'] = True
            base_opts['writeautomaticsub'] = True
            base_opts['subtitleslangs'] = ['en', 'en-US', 'en-GB']
        
        return base_opts
    
    def progress_hook(self, d: Dict):
        """Enhanced progress hook with better state management"""
        try:
            status = d.get('status', 'unknown')
            
            if status == 'downloading':
                # Extract progress information
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                else:
                    progress = 0
                
                speed = d.get('_speed_str', 'Unknown')
                eta = d.get('_eta_str', 'Unknown')
                
                self.download_state.update({
                    'status': 'downloading',
                    'progress': min(progress, 100),
                    'speed': speed,
                    'eta': eta,
                    'total_bytes': total_bytes,
                    'downloaded_bytes': downloaded_bytes,
                    'error': None
                })
                
            elif status == 'finished':
                self.download_state.update({
                    'status': 'finished',
                    'progress': 100,
                    'speed': '',
                    'eta': 'Complete',
                    'error': None
                })
                
            elif status == 'error':
                self.download_state.update({
                    'status': 'error',
                    'error': d.get('error', 'Unknown error occurred')
                })
                
        except Exception as e:
            logger.error(f"Progress hook error: {e}")
    
    def download_video(self, url: str, ydl_opts: Dict, progress_container) -> bool:
        """Enhanced download method with better error handling"""
        self.download_state = {
            'status': 'starting',
            'progress': 0,
            'speed': '',
            'eta': '',
            'error': None,
            'total_bytes': 0,
            'downloaded_bytes': 0
        }
        
        # Add progress hook
        ydl_opts['progress_hooks'] = [self.progress_hook]
        
        try:
            def download_task():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    return True
                except Exception as e:
                    self.download_state['status'] = 'error'
                    self.download_state['error'] = str(e)
                    return False
            
            # Run download in thread to avoid blocking Streamlit
            future = self.executor.submit(download_task)
            
            # Progress tracking
            progress_bar = progress_container.progress(0)
            status_text = progress_container.empty()
            
            # Monitor progress
            while not future.done():
                state = self.download_state
                status = state['status']
                progress = state['progress']
                
                if status == 'downloading':
                    progress_bar.progress(int(min(progress, 100)))
                    speed = state['speed']
                    eta = state['eta']
                    
                    if state['total_bytes'] > 0:
                        total_mb = state['total_bytes'] / (1024 * 1024)
                        downloaded_mb = state['downloaded_bytes'] / (1024 * 1024)
                        status_text.info(f"📥 Downloading... {progress:.1f}% | {downloaded_mb:.1f}MB / {total_mb:.1f}MB | Speed: {speed} | ETA: {eta}")
                    else:
                        status_text.info(f"📥 Downloading... {progress:.1f}% | Speed: {speed}")
                        
                elif status == 'starting':
                    status_text.info("🚀 Starting download...")
                    
                elif status == 'error':
                    break
                
                time.sleep(0.5)  # Update every 500ms
            
            # Get final result
            success = future.result(timeout=5)  # Wait max 5 seconds for result
            
            if success and self.download_state['status'] != 'error':
                progress_bar.progress(100)
                status_text.success("✅ Download completed successfully!")
                return True
            else:
                error = self.download_state.get('error', 'Unknown error occurred')
                self.show_error_details(error, progress_container, url)
                return False
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Download failed: {error_msg}")
            self.show_error_details(error_msg, progress_container, url)
            return False
    
    def show_error_details(self, error_msg: str, container, url: str):
        """Show detailed error information and suggestions"""
        container.empty()
        
        st.error("❌ Download failed!")
        
        with st.expander("🔍 Error Details & Solutions", expanded=True):
            st.code(error_msg, language="text")
            
            error_lower = error_msg.lower()
            
            # Provide specific solutions based on error type
            if "429" in error_msg or "too many requests" in error_lower:
                st.warning("**Rate Limiting Issue**")
                st.write("The server is rate-limiting requests. Solutions:")
                st.write("• Wait 5-10 minutes before trying again")
                st.write("• Try downloading without subtitles")
                st.write("• Use a VPN to change your IP address")
                
            elif "private" in error_lower or "unavailable" in error_lower:
                st.warning("**Video Access Issue**")
                st.write("• Video is private or has been removed")
                st.write("• Check if the URL is correct")
                st.write("• Video might be restricted in your region")
                
            elif "copyright" in error_lower:
                st.error("**Copyright Protected**")
                st.write("This video cannot be downloaded due to copyright restrictions.")
                
            elif "geo" in error_lower or "blocked" in error_lower:
                st.warning("**Geographic Restriction**")
                st.write("• Video is blocked in your region")
                st.write("• Try using a VPN")
                st.write("• Some content is region-specific")
                
            elif "fragment" in error_lower or "m3u8" in error_lower:
                st.info("**Streaming Format Issue**")
                st.write("• Live streams or adaptive formats detected")
                st.write("• Try a different quality setting")
                st.write("• Some live content cannot be downloaded")
                
            else:
                st.info("**General Troubleshooting**")
                st.write("• Check your internet connection")
                st.write("• Try a different video quality")
                st.write("• Restart the application if issues persist")
                
            # Quick retry options
            st.markdown("---")
            st.write("**Quick Fixes:**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🎵 Try Audio Only", key=f"audio_fix_{time.time()}"):
                    self.quick_audio_download(url, container)
                    
            with col2:
                if st.button("📱 Try Lowest Quality", key=f"low_fix_{time.time()}"):
                    self.quick_low_quality_download(url, container)
                    
            with col3:
                if st.button("🔄 Retry Original", key=f"retry_fix_{time.time()}"):
                    st.rerun()
    
    def quick_audio_download(self, url: str, container):
        """Quick audio-only download as fallback"""
        container.empty()
        st.info("🎵 Trying audio-only download...")
        
        config = {
            'type': 'audio_only',
            'quality': 'best',
            'format': 'mp3',
            'additional': {}
        }
        
        ydl_opts = self.build_ydl_opts(url, config)
        progress_container = st.empty()
        
        success = self.download_video(url, ydl_opts, progress_container)
        return success
    
    def quick_low_quality_download(self, url: str, container):
        """Quick low-quality download as fallback"""
        container.empty()
        st.info("📱 Trying lowest quality download...")
        
        config = {
            'type': 'video_audio',
            'quality': '360p',
            'format': 'mp4',
            'additional': {}
        }
        
        ydl_opts = self.build_ydl_opts(url, config)
        progress_container = st.empty()
        
        success = self.download_video(url, ydl_opts, progress_container)
        return success
    
    def get_downloaded_files(self) -> List[Path]:
        """Get list of downloaded files"""
        try:
            files = []
            temp_path = Path(self.temp_dir)
            
            if temp_path.exists():
                for file_path in temp_path.iterdir():
                    if file_path.is_file() and file_path.stat().st_size > 0:
                        files.append(file_path)
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return files
        
        except Exception as e:
            logger.error(f"Error getting downloaded files: {e}")
            return []
    
    def cleanup_files(self):
        """Clean up downloaded files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = tempfile.mkdtemp(prefix="yt_downloader_")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


def main():
    """Main Streamlit application"""
    
    # Initialize session state
    if 'downloader' not in st.session_state:
        st.session_state.downloader = EnhancedYouTubeDownloader()
    
    if 'video_info' not in st.session_state:
        st.session_state.video_info = None
    
    if 'show_formats' not in st.session_state:
        st.session_state.show_formats = False
    
    if 'last_url' not in st.session_state:
        st.session_state.last_url = ""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎬 YouTube Downloader Pro</h1>
        <p>Professional video downloader</p>
        <small>Powered by yt-dlp • Built with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Download Configuration")
        
        # URL Input with validation
        url = st.text_input(
            "🔗 YouTube URL",
            placeholder="https://youtube.com/watch?v=...",
            help="Enter a valid YouTube video URL",
            value=st.session_state.last_url
        )
        
        # URL validation feedback
        if url:
            if st.session_state.downloader.is_valid_youtube_url(url):
                st.success("✅ Valid YouTube URL")
            else:
                st.error("❌ Invalid YouTube URL")
        
        # Get video info button
        if st.button("🔍 Get Video Info", type="primary", use_container_width=True):
            if url and st.session_state.downloader.is_valid_youtube_url(url):
                try:
                    with st.spinner("🔄 Fetching video information..."):
                        info = st.session_state.downloader.get_video_info(url)
                        st.session_state.video_info = info
                        st.session_state.show_formats = False
                        st.session_state.last_url = url
                        st.success("✅ Video info loaded successfully!")
                        time.sleep(0.5)
                        st.rerun()
                        
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
            else:
                st.error("❌ Please enter a valid YouTube URL")
        
        # Cleanup button
        st.markdown("---")
        if st.button("🗑️ Clear Downloads", use_container_width=True):
            st.session_state.downloader.cleanup_files()
            st.success("✅ Downloads cleared")
    
    # Main content area
    if st.session_state.video_info:
        info = st.session_state.video_info
        
        # Video Information Display
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📺 Video Information")
            
            # Enhanced video info card
            title = info.get('title', 'Unknown Title')
            uploader = info.get('uploader', 'Unknown')
            duration = st.session_state.downloader.format_duration(info.get('duration'))
            views = st.session_state.downloader.format_number(info.get('view_count'))
            upload_date = info.get('upload_date', 'Unknown')
            
            # Format upload date
            if upload_date and len(upload_date) == 8:
                try:
                    formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                except:
                    formatted_date = upload_date
            else:
                formatted_date = upload_date
            
            st.markdown(f"""
            <div class="video-info-card">
                <h4>🎬 {title}</h4>
                <p><strong>👤 Channel:</strong> {uploader}</p>
                <p><strong>⏱️ Duration:</strong> {duration}</p>
                <p><strong>👁️ Views:</strong> {views}</p>
                <p><strong>📅 Upload Date:</strong> {formatted_date}</p>
                <p><strong>🔗 Video ID:</strong> {info.get('id', 'Unknown')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Video description (truncated)
            if info.get('description'):
                with st.expander("📄 Description"):
                    st.write(info['description'])
        
        with col2:
            # Thumbnail with better error handling
            if info.get('thumbnail'):
                try:
                    st.image(info['thumbnail'], caption="Video Thumbnail", use_column_width=True)
                except:
                    st.info("🖼️ Thumbnail not available")
            else:
                st.info("🖼️ No thumbnail available")
        
        # Available formats section
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Show Available Formats", use_container_width=True):
                st.session_state.show_formats = True
        
        with col2:
            if st.button("🔄 Refresh Video Info", use_container_width=True):
                try:
                    with st.spinner("🔄 Refreshing..."):
                        updated_info = st.session_state.downloader.get_video_info(url)
                        st.session_state.video_info = updated_info
                        st.success("✅ Video info refreshed!")
                        time.sleep(0.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Refresh failed: {str(e)}")
        
        # Display formats if requested
        if st.session_state.show_formats:
            try:
                video_formats, audio_formats, combined_formats = st.session_state.downloader.get_available_formats(info)
                
                st.markdown("### 🎯 Available Download Formats")
                
                format_tabs = st.tabs(["🎬 Video + Audio", "📹 Video Only", "🎵 Audio Only"])
                
                with format_tabs[0]:
                    if combined_formats:
                        st.info(f"📊 Found {len(combined_formats)} combined formats")
                        for i, fmt in enumerate(combined_formats[:12], 1):
                            height = fmt.get('height', 'Unknown')
                            fps = fmt.get('fps', 'Unknown')
                            ext = fmt.get('ext', 'Unknown').upper()
                            filesize = st.session_state.downloader.format_filesize(fmt.get('filesize'))
                            vcodec = fmt.get('vcodec', 'Unknown')
                            acodec = fmt.get('acodec', 'Unknown')
                            
                            st.markdown(f"""
                            <div class="format-card">
                                <strong>{height}p @ {fps}fps</strong> | {ext} | {filesize}<br>
                                <small>Video: {vcodec} | Audio: {acodec}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ No combined video+audio formats available. Use separate video and audio downloads.")
                
                with format_tabs[1]:
                    if video_formats:
                        st.info(f"📊 Found {len(video_formats)} video-only formats")
                        for i, fmt in enumerate(video_formats[:12], 1):
                            height = fmt.get('height', 'Unknown')
                            fps = fmt.get('fps', 'Unknown')
                            ext = fmt.get('ext', 'Unknown').upper()
                            filesize = st.session_state.downloader.format_filesize(fmt.get('filesize'))
                            vcodec = fmt.get('vcodec', 'Unknown')
                            
                            st.markdown(f"""
                            <div class="format-card">
                                <strong>{height}p @ {fps}fps</strong> | {ext} | {filesize}<br>
                                <small>Codec: {vcodec}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("ℹ️ No video-only formats available")
                
                with format_tabs[2]:
                    if audio_formats:
                        st.info(f"📊 Found {len(audio_formats)} audio-only formats")
                        for i, fmt in enumerate(audio_formats[:10], 1):
                            abr = fmt.get('abr', 'Unknown')
                            ext = fmt.get('ext', 'Unknown').upper()
                            filesize = st.session_state.downloader.format_filesize(fmt.get('filesize'))
                            acodec = fmt.get('acodec', 'Unknown')
                            
                            st.markdown(f"""
                            <div class="format-card">
                                <strong>{abr}kbps</strong> | {ext} | {filesize}<br>
                                <small>Codec: {acodec}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("ℹ️ No audio-only formats available")
                        
            except Exception as e:
                st.error(f"❌ Error loading formats: {str(e)}")
        
        # Download Configuration Section
        st.markdown("---")
        st.markdown("### ⬇️ Download Configuration")
        
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                download_type = st.selectbox(
                    "📥 Download Type",
                    options=["video_audio", "video_only", "audio_only"],
                    format_func=lambda x: {
                        "video_audio": "🎬 Video + Audio",
                        "video_only": "📹 Video Only", 
                        "audio_only": "🎵 Audio Only"
                    }[x],
                    help="Choose what to download"
                )
            
            with col2:
                if download_type in ["video_audio", "video_only"]:
                    quality_options = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "worst"]
                    quality_labels = {
                        "best": "🏆 Best Available",
                        "2160p": "🔥 4K (2160p)",
                        "1440p": "⭐ 2K (1440p)", 
                        "1080p": "💎 Full HD (1080p)",
                        "720p": "📺 HD (720p)",
                        "480p": "📱 SD (480p)",
                        "360p": "📱 Low (360p)",
                        "worst": "💾 Smallest File"
                    }
                    
                    quality = st.selectbox(
                        "🎯 Quality",
                        options=quality_options,
                        format_func=lambda x: quality_labels[x],
                        help="Select video quality"
                    )
                    
                elif download_type == "audio_only":
                    quality_options = ["best", "320k", "256k", "192k", "128k", "96k"]
                    quality_labels = {
                        "best": "🏆 Best Quality",
                        "320k": "🔥 320 kbps",
                        "256k": "⭐ 256 kbps",
                        "192k": "💎 192 kbps", 
                        "128k": "📻 128 kbps",
                        "96k": "💾 96 kbps"
                    }
                    
                    quality = st.selectbox(
                        "🎵 Audio Quality",
                        options=quality_options,
                        format_func=lambda x: quality_labels[x],
                        help="Select audio quality"
                    )
            
            with col3:
                if download_type in ["video_audio", "video_only"]:
                    format_options = ["mp4", "mkv", "webm", "avi"]
                    format_labels = {
                        "mp4": "📹 MP4 (Recommended)",
                        "mkv": "🎬 MKV",
                        "webm": "🌐 WebM",
                        "avi": "📼 AVI"
                    }
                    
                    output_format = st.selectbox(
                        "📁 Output Format",
                        options=format_options,
                        format_func=lambda x: format_labels[x],
                        help="Choose output video format"
                    )
                    
                elif download_type == "audio_only":
                    format_options = ["mp3", "aac", "flac", "wav", "ogg"]
                    format_labels = {
                        "mp3": "🎵 MP3 (Universal)",
                        "aac": "🔊 AAC (High Quality)",
                        "flac": "🎼 FLAC (Lossless)",
                        "wav": "🎙️ WAV (Uncompressed)",
                        "ogg": "🔉 OGG"
                    }
                    
                    output_format = st.selectbox(
                        "🎵 Audio Format",
                        options=format_options,
                        format_func=lambda x: format_labels[x],
                        help="Choose output audio format"
                    )
        
        # Additional options
        st.markdown("#### ⚙️ Additional Options")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            download_thumbnail = st.checkbox("🖼️ Thumbnail", help="Download video thumbnail")
        with col2:
            download_description = st.checkbox("📄 Description", help="Save video description")
        with col3:
            download_subtitles = st.checkbox("📝 Subtitles", help="Download subtitles (may cause rate limiting)")
        with col4:
            if download_subtitles:
                st.warning("⚠️ Subtitles may cause rate limiting (HTTP 429 errors)")
        
        # Build download configuration
        download_config = {
            'type': download_type,
            'quality': quality,
            'format': output_format,
            'additional': {
                'thumbnail': download_thumbnail,
                'description': download_description,
                'subtitles': download_subtitles
            }
        }
        
        # Download buttons
        st.markdown("---")
        st.markdown("### 🚀 Download Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Start Download", type="primary", use_container_width=True):
                try:
                    # Build yt-dlp options
                    ydl_opts = st.session_state.downloader.build_ydl_opts(url, download_config)
                    
                    # Create progress container
                    progress_container = st.empty()
                    
                    # Start download
                    with st.spinner("🔄 Preparing download..."):
                        success = st.session_state.downloader.download_video(url, ydl_opts, progress_container)
                    
                    if success:
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Download setup failed: {str(e)}")
        
        with col2:
            if st.button("🎵 Quick Audio (MP3)", use_container_width=True):
                quick_config = {
                    'type': 'audio_only',
                    'quality': 'best', 
                    'format': 'mp3',
                    'additional': {}
                }
                try:
                    ydl_opts = st.session_state.downloader.build_ydl_opts(url, quick_config)
                    progress_container = st.empty()
                    
                    with st.spinner("🎵 Downloading audio..."):
                        success = st.session_state.downloader.download_video(url, ydl_opts, progress_container)
                    
                    if success:
                        st.success("✅ Audio download completed!")
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Audio download failed: {str(e)}")
        
        with col3:
            if st.button("📱 Quick Low Quality", use_container_width=True):
                quick_config = {
                    'type': 'video_audio',
                    'quality': '360p',
                    'format': 'mp4', 
                    'additional': {}
                }
                try:
                    ydl_opts = st.session_state.downloader.build_ydl_opts(url, quick_config)
                    progress_container = st.empty()
                    
                    with st.spinner("📱 Downloading low quality..."):
                        success = st.session_state.downloader.download_video(url, ydl_opts, progress_container)
                    
                    if success:
                        st.success("✅ Low quality download completed!")
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Low quality download failed: {str(e)}")
        
        # Downloaded files section
        downloaded_files = st.session_state.downloader.get_downloaded_files()
        
        if downloaded_files:
            st.markdown("---")
            st.markdown("### 📁 Downloaded Files")
            
            # Show total files and size
            total_size = sum(f.stat().st_size for f in downloaded_files)
            total_size_formatted = st.session_state.downloader.format_filesize(total_size)
            
            st.info(f"📊 {len(downloaded_files)} files • Total size: {total_size_formatted}")
            
            # Display each file with download button
            for i, file_path in enumerate(downloaded_files):
                file_size = file_path.stat().st_size
                formatted_size = st.session_state.downloader.format_filesize(file_size)
                
                # Determine file type icon
                ext = file_path.suffix.lower()
                if ext in ['.mp4', '.mkv', '.webm', '.avi']:
                    icon = "🎬"
                elif ext in ['.mp3', '.aac', '.flac', '.wav', '.ogg']:
                    icon = "🎵"
                elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    icon = "🖼️"
                elif ext in ['.vtt', '.srt']:
                    icon = "📝"
                else:
                    icon = "📄"
                
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.write(f"{icon} **{file_path.name}**")
                    st.caption(f"Size: {formatted_size} • Modified: {time.ctime(file_path.stat().st_mtime)}")
                
                with col2:
                    try:
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                            
                        # Determine MIME type
                        if ext in ['.mp4', '.mkv', '.webm', '.avi']:
                            mime_type = 'video/mp4'
                        elif ext in ['.mp3']:
                            mime_type = 'audio/mpeg'
                        elif ext in ['.aac', '.m4a']:
                            mime_type = 'audio/aac'
                        elif ext in ['.flac']:
                            mime_type = 'audio/flac'
                        elif ext in ['.wav']:
                            mime_type = 'audio/wav'
                        elif ext in ['.ogg']:
                            mime_type = 'audio/ogg'
                        elif ext in ['.jpg', '.jpeg']:
                            mime_type = 'image/jpeg'
                        elif ext in ['.png']:
                            mime_type = 'image/png'
                        else:
                            mime_type = 'application/octet-stream'
                        
                        st.download_button(
                            "💾 Download",
                            data=file_data,
                            file_name=file_path.name,
                            mime=mime_type,
                            use_container_width=True,
                            key=f"download_{i}_{file_path.name}"
                        )
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                
                if i < len(downloaded_files) - 1:
                    st.markdown("---")
    
    else:
        # Welcome screen with enhanced features
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h2>🎬 Welcome to YouTube Downloader Pro!</h2>
            <p style="font-size: 1.1em; color: #666; margin-bottom: 2rem;">
                Professional video downloader with enhanced error handling, progress tracking, and multiple format support.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature highlights
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>🎯 Smart Format Detection</h3>
                <p>Automatically detects and suggests the best available formats for your video with detailed quality information.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>⚡ Enhanced Error Handling</h3>
                <p>Advanced error detection with specific solutions for common issues like rate limiting, geo-blocking, and format problems.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>🔄 Real-time Progress</h3>
                <p>Live progress tracking with speed, ETA, and detailed download statistics for better user experience.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Usage instructions
        st.markdown("---")
        st.markdown("### 🚀 Quick Start Guide")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("""
            **Step 1:** Enter YouTube URL in the sidebar  
            **Step 2:** Click "Get Video Info" to load details  
            **Step 3:** Choose your preferred quality and format  
            **Step 4:** Click "Start Download" and wait for completion  
            **Step 5:** Download your files using the download buttons
            """)
        
        with col2:
            st.markdown("""
            **Supported Formats:**
            - 🎬 Video: MP4, MKV, WebM, AVI
            - 🎵 Audio: MP3, AAC, FLAC, WAV, OGG
            - 📝 Subtitles: VTT, SRT (English)
            - 🖼️ Thumbnails: JPG, PNG
            - 📄 Descriptions: TXT
            """)
        
        # Tips and warnings
        st.markdown("---")
        st.markdown("### 💡 Tips & Important Notes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("""
            **✅ Best Practices:**
            - Use MP4 format for maximum compatibility
            - Choose appropriate quality for your needs
            - Download audio-only for music content
            - Clear downloads regularly to save space
            """)
        
        with col2:
            st.warning("""
            **⚠️ Important Warnings:**
            - Respect copyright and terms of service
            - Some content may be geo-restricted
            - Live streams cannot be downloaded
            - Subtitles may trigger rate limiting
            """)


if __name__ == "__main__":
    # Check dependencies
    try:
        import yt_dlp
    except ImportError:
        st.error("""
        ❌ **Missing Dependencies**
        
        Please install required packages:
        ```bash
        pip install yt-dlp streamlit
        ```
        
        Optional (for better format support):
        ```bash
        pip install ffmpeg-python
        ```
        """)
        st.stop()
    
    # Check Python version
    if sys.version_info < (3, 8):
        st.error("❌ Python 3.8+ is required. Please upgrade your Python version.")
        st.stop()
    
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.code(traceback.format_exc(), language="python")
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Solutions:**
            1. Restart the application
            2. Clear browser cache
            3. Check internet connection
            4. Update dependencies: `pip install --upgrade yt-dlp streamlit`
            5. Make sure you have sufficient disk space
            """)
