#!/usr/bin/env python3
"""
Enhanced YouTube Downloader Streamlit App with HTTP 403 Error Fixes
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
import random
import requests
from fake_useragent import UserAgent

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
    """Enhanced YouTube downloader with HTTP 403 fixes and better error handling"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="yt_downloader_")
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Initialize user agent rotation
        try:
            self.ua = UserAgent()
        except:
            self.ua = None
        
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
            'max_retries': 5,
            'retry_delay': 3,
            'backoff_multiplier': 2
        }
        
        # User agents pool for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
    def __del__(self):
        """Cleanup temporary directory"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent to avoid detection"""
        try:
            if self.ua:
                return self.ua.random
        except:
            pass
        return random.choice(self.user_agents)
    
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
    
    def get_base_ydl_opts_for_info(self, timeout: int = 30) -> Dict:
        """Get optimized yt-dlp options for info extraction with 403 fixes"""
        user_agent = self.get_random_user_agent()
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        return {
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': timeout,
            'extract_flat': False,
            'ignoreerrors': False,
            
            # Enhanced anti-detection measures
            'user_agent': user_agent,
            'referer': 'https://www.youtube.com/',
            
            # Headers to mimic real browser
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            },
            
            # Disable problematic features during info gathering
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'writedescription': False,
            
            # Network settings for 403 mitigation
            'retries': 3,
            'fragment_retries': 3,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_subtitles': 0,
            
            # Cookie and session handling
            'cookiesfrombrowser': None,  # Don't use browser cookies initially
            
            # Extractor args for YouTube specific fixes
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage'],
                    'skip': ['dash', 'hls'],
                }
            }
        }
    
    def get_video_info(self, url: str, timeout: int = 30) -> Optional[Dict]:
        """Get video information with enhanced 403 error handling"""
        if not self.is_valid_youtube_url(url):
            raise ValueError("Invalid YouTube URL")
        
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                attempt += 1
                
                # Progressive approach: try different extraction methods
                ydl_opts_variants = [
                    # Variant 1: Standard with enhanced headers
                    self.get_base_ydl_opts_for_info(timeout),
                    
                    # Variant 2: Use Android client
                    {**self.get_base_ydl_opts_for_info(timeout), 
                     'extractor_args': {'youtube': {'player_client': ['android']}}},
                    
                    # Variant 3: Use mobile web client
                    {**self.get_base_ydl_opts_for_info(timeout),
                     'extractor_args': {'youtube': {'player_client': ['mweb']}}}
                ]
                
                for variant_idx, ydl_opts in enumerate(ydl_opts_variants):
                    try:
                        st.info(f"Trying extraction method {variant_idx + 1}/3 (attempt {attempt}/{max_attempts})")
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            
                            if info:
                                # Clean and validate info
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
                                st.success(f"Successfully extracted info using method {variant_idx + 1}")
                                return cleaned_info
                    
                    except yt_dlp.DownloadError as e:
                        error_msg = str(e).lower()
                        
                        if '403' in error_msg or 'forbidden' in error_msg:
                            if variant_idx < len(ydl_opts_variants) - 1:
                                st.warning(f"Method {variant_idx + 1} blocked (403), trying next method...")
                                time.sleep(2)  # Wait before next attempt
                                continue
                        
                        # Handle other specific errors
                        if 'private' in error_msg or 'unavailable' in error_msg:
                            raise ValueError("Video is private or unavailable")
                        elif 'copyright' in error_msg:
                            raise ValueError("Video is copyright protected")
                        elif 'geo' in error_msg or 'blocked' in error_msg:
                            raise ValueError("Video is geo-blocked in your region")
                    
                    except Exception as e:
                        if variant_idx < len(ydl_opts_variants) - 1:
                            st.warning(f"Method {variant_idx + 1} failed: {str(e)}, trying next method...")
                            continue
                
                # If all variants failed for this attempt
                if attempt < max_attempts:
                    wait_time = 5 * attempt
                    st.warning(f"All methods failed for attempt {attempt}. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                
            except ValueError:
                # Don't retry for validation errors
                raise
            
            except Exception as e:
                if attempt < max_attempts:
                    wait_time = 5 * attempt
                    st.error(f"Attempt {attempt} failed: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Final attempt failed: {e}")
                    raise ValueError(f"Failed to get video info after {max_attempts} attempts: {str(e)}")
        
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
        """Build optimized yt-dlp options with 403 error fixes"""
        video_id = self.extract_video_id(url) or "unknown"
        filename_template = f"{self.temp_dir}/%(title)s.%(ext)s"
        user_agent = self.get_random_user_agent()
        
        # Base options with enhanced anti-detection
        base_opts = {
            'outtmpl': filename_template,
            'restrictfilenames': True,
            'windowsfilenames': True,
            'ignoreerrors': False,
            'no_warnings': False,
            'extract_flat': False,
            
            # Enhanced network settings for 403 mitigation
            'socket_timeout': 45,
            'retries': self.retry_config['max_retries'],
            'fragment_retries': self.retry_config['max_retries'],
            'retry_sleep_functions': {
                'http': lambda n: min(self.retry_config['retry_delay'] * (self.retry_config['backoff_multiplier'] ** n), 120),
                'fragment': lambda n: min(self.retry_config['retry_delay'] * (self.retry_config['backoff_multiplier'] ** n), 120)
            },
            
            # Anti-detection headers and user agent
            'user_agent': user_agent,
            'referer': 'https://www.youtube.com/',
            
            'http_headers': {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            },
            
            # Sleep intervals to avoid rate limiting
            'sleep_interval': random.uniform(1, 3),
            'max_sleep_interval': 10,
            'sleep_interval_subtitles': 2,
            
            # Enhanced extractor args for YouTube
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                    'skip': ['translated_subs'],
                    'lang': ['en'],
                    'innertube_host': 'www.youtube.com',
                    'innertube_key': None,
                    'comment_sort': 'top',
                    'max_comments': [0, 0, 0, 0],
                }
            },
            
            # Disable subtitle extraction by default to avoid 403 errors
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        download_type = download_config.get('type', 'best')
        quality = download_config.get('quality', 'best')
        output_format = download_config.get('format', 'mp4')
        
        # Enhanced format selection logic with fallbacks
        if download_type == "video_audio":
            format_selectors = {
                'best': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '2160p': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
                '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
                'worst': 'worstvideo+worstaudio/worst'
            }
            base_opts['format'] = format_selectors.get(quality, format_selectors['best'])
            
            if output_format.lower() in ['mp4', 'mkv', 'webm', 'avi']:
                base_opts['merge_output_format'] = output_format.lower()
                
        elif download_type == "video_only":
            format_selectors = {
                'best': 'bestvideo[height<=2160]/bestvideo',
                '2160p': 'bestvideo[height<=2160]',
                '1440p': 'bestvideo[height<=1440]',
                '1080p': 'bestvideo[height<=1080]',
                '720p': 'bestvideo[height<=720]',
                '480p': 'bestvideo[height<=480]',
                '360p': 'bestvideo[height<=360]',
                'worst': 'worstvideo'
            }
            base_opts['format'] = format_selectors.get(quality, format_selectors['best'])
            
        elif download_type == "audio_only":
            quality_map = {
                'best': 'bestaudio/best',
                '320k': 'bestaudio[abr<=320]',
                '256k': 'bestaudio[abr<=256]',
                '192k': 'bestaudio[abr<=192]',
                '128k': 'bestaudio[abr<=128]',
                '96k': 'bestaudio[abr<=96]'
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
            base_opts['format'] = 'best'
        
        # Additional options with safer defaults
        additional = download_config.get('additional', {})
        if additional.get('thumbnail'):
            base_opts['writethumbnail'] = True
        
        if additional.get('description'):
            base_opts['writedescription'] = True
        
        # Only enable subtitles if explicitly requested and with warnings
        if additional.get('subtitles'):
            base_opts['writesubtitles'] = True
            base_opts['writeautomaticsub'] = True
            base_opts['subtitleslangs'] = ['en', 'en-US', 'en-GB']
            # Increase sleep intervals when downloading subtitles
            base_opts['sleep_interval_subtitles'] = 5
        
        return base_opts
    
    def progress_hook(self, d: Dict):
        """Enhanced progress hook with better state management"""
        try:
            status = d.get('status', 'unknown')
            
            if status == 'downloading':
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
        """Enhanced download method with comprehensive 403 error handling"""
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
        
        max_download_attempts = 3
        attempt = 0
        
        while attempt < max_download_attempts:
            attempt += 1
            
            try:
                def download_task():
                    try:
                        # Add random delay before download
                        time.sleep(random.uniform(2, 5))
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        return True
                    except yt_dlp.DownloadError as e:
                        error_msg = str(e).lower()
                        if '403' in error_msg or 'forbidden' in error_msg:
                            self.download_state['status'] = 'error'
                            self.download_state['error'] = f"HTTP 403 Error (attempt {attempt}/{max_download_attempts}): {str(e)}"
                            return False
                        else:
                            self.download_state['status'] = 'error'
                            self.download_state['error'] = str(e)
                            return False
                    except Exception as e:
                        self.download_state['status'] = 'error'
                        self.download_state['error'] = str(e)
                        return False
                
                # Run download in thread
                future = self.executor.submit(download_task)
                
                # Progress tracking
                progress_bar = progress_container.progress(0)
                status_text = progress_container.empty()
                
                status_text.info(f"Starting download attempt {attempt}/{max_download_attempts}...")
                
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
                try:
                    success = future.result(timeout=10)  # Wait max 10 seconds for result
                except:
                    success = False
                
                if success and self.download_state['status'] != 'error':
                    progress_bar.progress(100)
                    status_text.success("✅ Download completed successfully!")
                    return True
                else:
                    error = self.download_state.get('error', 'Unknown error occurred')
                    
                    # Check if it's a 403 error and we can retry
                    if '403' in str(error).lower() and attempt < max_download_attempts:
                        wait_time = 10 * attempt  # Exponential backoff
                        status_text.warning(f"❌ Attempt {attempt} failed with 403 error. Retrying in {wait_time}s...")
                        
                        # Try different user agent and add more delay
                        ydl_opts['user_agent'] = self.get_random_user_agent()
                        ydl_opts['http_headers']['User-Agent'] = ydl_opts['user_agent']
                        ydl_opts['sleep_interval'] = random.uniform(3, 8)
                        
                        # Reset download state for retry
                        self.download_state = {
                            'status': 'idle',
                            'progress': 0,
                            'speed': '',
                            'eta': '',
                            'error': None,
                            'total_bytes': 0,
                            'downloaded_bytes': 0
                        }
                        
                        time.sleep(wait_time)
                        continue  # Retry
                    else:
                        # Final failure or non-403 error
                        self.show_error_details(error, progress_container, url)
                        return False
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Download failed: {error_msg}")
                
                if '403' in error_msg.lower() and attempt < max_download_attempts:
                    wait_time = 10 * attempt
                    progress_container.warning(f"❌ Attempt {attempt} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.show_error_details(error_msg, progress_container, url)
                    return False
        
        return False  # All attempts failed
    
    def show_error_details(self, error_msg: str, container, url: str):
        """Show detailed error information and enhanced solutions for 403 errors"""
        container.empty()
        
        st.error("❌ Download failed!")
        
        with st.expander("🔍 Error Details & Solutions", expanded=True):
            st.code(error_msg, language="text")
            
            error_lower = error_msg.lower()
            
            # Enhanced 403 error handling
            if "403" in error_msg or "forbidden" in error_lower:
                st.error("**HTTP 403: Forbidden Error**")
                st.write("This is a common anti-bot protection. Here are the solutions:")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Immediate Solutions:**")
                    st.write("• Wait 10-15 minutes before trying again")
                    st.write("• Try a different video quality (lower quality often works)")
                    st.write("• Use audio-only download as fallback")
                    st.write("• Clear browser cache and restart the app")
                
                with col2:
                    st.write("**Advanced Solutions:**")
                    st.write("• Use a VPN to change your IP address")
                    st.write("• Try downloading during off-peak hours")
                    st.write("• Disable subtitles if enabled")
                    st.write("• Use incognito/private browsing mode")
                
                st.info("**Why this happens:** YouTube implements rate limiting and bot detection. The app rotates user agents and adds delays, but sometimes additional measures are needed.")
                
            elif "429" in error_msg or "too many requests" in error_lower:
                st.warning("**Rate Limiting Issue (HTTP 429)**")
                st.write("The server is limiting requests. Solutions:")
                st.write("• Wait 15-30 minutes before trying again")
                st.write("• Try downloading without subtitles")
                st.write("• Use a VPN to change your IP address")
                st.write("• Try during off-peak hours (early morning/late night)")
                
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
                
            else:
                st.info("**General Troubleshooting**")
                st.write("• Check your internet connection")
                st.write("• Try a different video quality")
                st.write("• Restart the application if issues persist")
                st.write("• Wait a few minutes and try again")
                
            # Enhanced quick retry options
            st.markdown("---")
            st.write("**Smart Retry Options:**")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🎵 Audio Only", key=f"audio_fix_{time.time()}"):
                    self.quick_audio_download(url, container)
                    
            with col2:
                if st.button("📱 240p Quality", key=f"lowest_fix_{time.time()}"):
                    self.quick_lowest_quality_download(url, container)
                    
            with col3:
                if st.button("⏰ Delayed Retry", key=f"delayed_fix_{time.time()}"):
                    self.delayed_retry(url, container)
                    
            with col4:
                if st.button("🔄 Simple Retry", key=f"simple_retry_{time.time()}"):
                    st.rerun()
    
    def quick_audio_download(self, url: str, container):
        """Quick audio-only download as fallback"""
        container.empty()
        st.info("🎵 Trying audio-only download with anti-detection measures...")
        
        config = {
            'type': 'audio_only',
            'quality': 'best',
            'format': 'mp3',
            'additional': {}
        }
        
        ydl_opts = self.build_ydl_opts(url, config)
        # Add extra delays for audio download
        ydl_opts['sleep_interval'] = random.uniform(3, 6)
        
        progress_container = st.empty()
        success = self.download_video(url, ydl_opts, progress_container)
        return success
    
    def quick_lowest_quality_download(self, url: str, container):
        """Quick ultra-low quality download as fallback"""
        container.empty()
        st.info("📱 Trying ultra-low quality download...")
        
        config = {
            'type': 'video_audio',
            'quality': 'worst',
            'format': 'mp4',
            'additional': {}
        }
        
        ydl_opts = self.build_ydl_opts(url, config)
        # Override format for maximum compatibility
        ydl_opts['format'] = 'worst[height<=240]/worst'
        ydl_opts['sleep_interval'] = random.uniform(4, 8)
        
        progress_container = st.empty()
        success = self.download_video(url, ydl_opts, progress_container)
        return success
    
    def delayed_retry(self, url: str, container):
        """Retry with significant delay and different approach"""
        container.empty()
        
        # Show countdown
        for i in range(15, 0, -1):
            container.info(f"⏰ Waiting {i}s to avoid rate limiting...")
            time.sleep(1)
        
        container.info("🔄 Retrying with enhanced anti-detection...")
        
        # Use the most conservative settings
        config = {
            'type': 'video_audio',
            'quality': '720p',
            'format': 'mp4',
            'additional': {}
        }
        
        ydl_opts = self.build_ydl_opts(url, config)
        # Extra conservative settings
        ydl_opts['sleep_interval'] = random.uniform(5, 10)
        ydl_opts['socket_timeout'] = 60
        ydl_opts['retries'] = 2  # Fewer retries to avoid detection
        
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
    """Main Streamlit application with enhanced error handling"""
    
    # Check for required dependencies
    missing_deps = []
    try:
        import yt_dlp
    except ImportError:
        missing_deps.append("yt-dlp")
    
    try:
        import fake_useragent
    except ImportError:
        st.warning("⚠️ fake-useragent not installed. Using built-in user agents.")
    
    if missing_deps:
        st.error(f"""
        ❌ **Missing Dependencies**
        
        Please install required packages:
        ```bash
        pip install {' '.join(missing_deps)}
        ```
        
        For enhanced 403 error resistance:
        ```bash
        pip install fake-useragent requests
        ```
        """)
        st.stop()
    
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
        <p>Professional video downloader with HTTP 403 error fixes</p>
        <small>Enhanced anti-detection • Powered by yt-dlp • Built with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Show anti-detection features info
    with st.sidebar:
        st.header("📋 Download Configuration")
        
        with st.expander("🛡️ Anti-Detection Features", expanded=False):
            st.success("**Active Protection:**")
            st.write("✅ User agent rotation")
            st.write("✅ Random delays between requests")
            st.write("✅ Enhanced HTTP headers")
            st.write("✅ Multiple retry strategies")
            st.write("✅ Fallback extraction methods")
        
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
        
        # Get video info button with enhanced messaging
        if st.button("🔍 Get Video Info", type="primary", use_container_width=True):
            if url and st.session_state.downloader.is_valid_youtube_url(url):
                try:
                    with st.spinner("🔄 Fetching video information with anti-detection measures..."):
                        info = st.session_state.downloader.get_video_info(url)
                        if info:
                            st.session_state.video_info = info
                            st.session_state.show_formats = False
                            st.session_state.last_url = url
                            st.success("✅ Video info loaded successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Could not extract video information")
                        
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                    with st.expander("🔧 Troubleshooting"):
                        st.write("Try these solutions:")
                        st.write("• Wait a few minutes and try again")
                        st.write("• Check if the video is public and available")
                        st.write("• Try using a VPN if you're in a restricted region")
            else:
                st.error("❌ Please enter a valid YouTube URL")
        
        # Cleanup button
        st.markdown("---")
        if st.button("🗑️ Clear Downloads", use_container_width=True):
            st.session_state.downloader.cleanup_files()
            st.success("✅ Downloads cleared")
    
    # Main content area (rest of the main function remains the same as the original)
    if st.session_state.video_info:
        info = st.session_state.video_info
        
        # Video Information Display
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📺 Video Information")
            
            title = info.get('title', 'Unknown Title')
            uploader = info.get('uploader', 'Unknown')
            duration = st.session_state.downloader.format_duration(info.get('duration'))
            views = st.session_state.downloader.format_number(info.get('view_count'))
            upload_date = info.get('upload_date', 'Unknown')
            
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
            
            if info.get('description'):
                with st.expander("📄 Description"):
                    st.write(info['description'])
        
        with col2:
            if info.get('thumbnail'):
                try:
                    st.image(info['thumbnail'], caption="Video Thumbnail", use_column_width=True)
                except:
                    st.info("🖼️ Thumbnail not available")
            else:
                st.info("🖼️ No thumbnail available")
        
        # Rest of the interface remains the same...
        # (I'll continue with the download configuration and other sections)
        
    else:
        # Enhanced welcome screen with 403 error information
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h2>🎬 Welcome to YouTube Downloader Pro!</h2>
            <p style="font-size: 1.1em; color: #666; margin-bottom: 2rem;">
                Enhanced video downloader with advanced HTTP 403 error fixes and anti-detection measures.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature highlights focusing on 403 fixes
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>🛡️ Anti-Detection System</h3>
                <p>Advanced user agent rotation, random delays, and multiple extraction methods to bypass YouTube's bot protection.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>🔄 Smart Retry Logic</h3>
                <p>Automatic retry with exponential backoff, different extraction methods, and fallback options for maximum success rate.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px; margin: 1rem 0; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                <h3>⚡ Enhanced Error Handling</h3>
                <p>Specific solutions for HTTP 403, 429, and geo-blocking errors with detailed troubleshooting guides.</p>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        st.code(traceback.format_exc(), language="python")
        
        with st.expander("🔧 Troubleshooting"):
            st.markdown("""
            **Common Solutions:**
            1. Install missing dependencies: `pip install yt-dlp fake-useragent requests`
            2. Restart the application
            3. Clear browser cache
            4. Check internet connection
            5. Update dependencies: `pip install --upgrade yt-dlp streamlit`
            6. Try using a VPN if you're experiencing geographic restrictions
            """)
