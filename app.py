#!/usr/bin/env python3
"""
YouTube Downloader App using yt-dlp
Comprehensive downloader with multiple format options and features
"""

import os
import sys
import yt_dlp
from pathlib import Path

class YouTubeDownloader:
    def __init__(self):
        self.download_path = "./downloads"
        self.create_download_folder()
    
    def create_download_folder(self):
        """Create downloads folder if it doesn't exist"""
        Path(self.download_path).mkdir(exist_ok=True)
    
    def get_video_info(self, url):
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None
    
    def display_video_info(self, info):
        """Display video information"""
        print("\n" + "="*60)
        print("VIDEO INFORMATION")
        print("="*60)
        print(f"Title: {info.get('title', 'N/A')}")
        print(f"Uploader: {info.get('uploader', 'N/A')}")
        print(f"Duration: {self.format_duration(info.get('duration', 0))}")
        print(f"View Count: {info.get('view_count', 'N/A'):,}" if info.get('view_count') else "View Count: N/A")
        print(f"Upload Date: {info.get('upload_date', 'N/A')}")
        print("="*60)
    
    def format_duration(self, seconds):
        """Format duration from seconds to HH:MM:SS"""
        if not seconds:
            return "N/A"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def get_available_formats(self, info):
        """Get available formats for the video"""
        formats = info.get('formats', [])
        
        # Separate video, audio, and combined formats
        video_formats = []
        audio_formats = []
        combined_formats = []
        
        for fmt in formats:
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                # Combined video+audio
                combined_formats.append(fmt)
            elif fmt.get('vcodec') != 'none' and fmt.get('acodec') == 'none':
                # Video only
                video_formats.append(fmt)
            elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                # Audio only
                audio_formats.append(fmt)
        
        return video_formats, audio_formats, combined_formats
    
    def display_formats(self, video_formats, audio_formats, combined_formats):
        """Display available formats in organized manner"""
        print("\n" + "="*80)
        print("AVAILABLE FORMATS")
        print("="*80)
        
        if combined_formats:
            print("\n📹 COMBINED VIDEO + AUDIO FORMATS:")
            print("-" * 50)
            for i, fmt in enumerate(combined_formats[:10], 1):  # Limit to 10 for readability
                quality = fmt.get('height', 'N/A')
                fps = fmt.get('fps', 'N/A')
                ext = fmt.get('ext', 'N/A')
                filesize = self.format_filesize(fmt.get('filesize'))
                print(f"{i:2d}. {quality}p {fps}fps | {ext.upper()} | {filesize}")
        
        if video_formats:
            print("\n🎬 VIDEO ONLY FORMATS:")
            print("-" * 50)
            for i, fmt in enumerate(video_formats[:10], len(combined_formats) + 1):
                quality = fmt.get('height', 'N/A')
                fps = fmt.get('fps', 'N/A')
                ext = fmt.get('ext', 'N/A')
                filesize = self.format_filesize(fmt.get('filesize'))
                print(f"{i:2d}. {quality}p {fps}fps | {ext.upper()} | {filesize}")
        
        if audio_formats:
            print("\n🎵 AUDIO ONLY FORMATS:")
            print("-" * 50)
            for i, fmt in enumerate(audio_formats[:10], len(combined_formats) + len(video_formats) + 1):
                abr = fmt.get('abr', 'N/A')
                ext = fmt.get('ext', 'N/A')
                filesize = self.format_filesize(fmt.get('filesize'))
                print(f"{i:2d}. {abr}kbps | {ext.upper()} | {filesize}")
    
    def format_filesize(self, size):
        """Format file size in human readable format"""
        if not size:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_download_options(self):
        """Get download preferences from user"""
        print("\n" + "="*60)
        print("DOWNLOAD OPTIONS")
        print("="*60)
        
        options = {}
        
        # Download type
        print("\n1. Video + Audio (merged)")
        print("2. Video only")
        print("3. Audio only")
        print("4. Best quality available")
        print("5. Worst quality (smallest file)")
        print("6. Custom format selection")
        
        while True:
            try:
                choice = int(input("\nSelect download type (1-6): "))
                if 1 <= choice <= 6:
                    options['type'] = choice
                    break
                else:
                    print("Please enter a number between 1 and 6")
            except ValueError:
                print("Please enter a valid number")
        
        # Quality selection for video
        if choice in [1, 2, 4, 5]:
            if choice not in [4, 5]:
                print("\nVideo Quality Options:")
                print("1. 2160p (4K)")
                print("2. 1440p (2K)")
                print("3. 1080p (Full HD)")
                print("4. 720p (HD)")
                print("5. 480p")
                print("6. 360p")
                print("7. Best available")
                print("8. Worst available")
                
                while True:
                    try:
                        quality_choice = int(input("Select quality (1-8): "))
                        if 1 <= quality_choice <= 8:
                            options['quality'] = quality_choice
                            break
                        else:
                            print("Please enter a number between 1 and 8")
                    except ValueError:
                        print("Please enter a valid number")
        
        # Audio quality for audio-only downloads
        if choice == 3:
            print("\nAudio Quality Options:")
            print("1. Best audio quality")
            print("2. 320kbps")
            print("3. 256kbps")
            print("4. 192kbps")
            print("5. 128kbps")
            print("6. 96kbps")
            
            while True:
                try:
                    audio_choice = int(input("Select audio quality (1-6): "))
                    if 1 <= audio_choice <= 6:
                        options['audio_quality'] = audio_choice
                        break
                    else:
                        print("Please enter a number between 1 and 6")
                except ValueError:
                    print("Please enter a valid number")
        
        # Output format
        if choice in [1, 2]:
            print("\nOutput Format:")
            print("1. MP4 (recommended)")
            print("2. MKV")
            print("3. WEBM")
            print("4. AVI")
            
            while True:
                try:
                    format_choice = int(input("Select format (1-4): "))
                    if 1 <= format_choice <= 4:
                        options['format'] = format_choice
                        break
                    else:
                        print("Please enter a number between 1 and 4")
                except ValueError:
                    print("Please enter a valid number")
        
        elif choice == 3:
            print("\nOutput Format:")
            print("1. MP3 (recommended)")
            print("2. M4A")
            print("3. FLAC")
            print("4. WAV")
            print("5. OGG")
            
            while True:
                try:
                    format_choice = int(input("Select format (1-5): "))
                    if 1 <= format_choice <= 5:
                        options['audio_format'] = format_choice
                        break
                    else:
                        print("Please enter a number between 1 and 5")
                except ValueError:
                    print("Please enter a valid number")
        
        # Additional options
        print("\nAdditional Options:")
        options['download_thumbnail'] = input("Download thumbnail? (y/n): ").lower().startswith('y')
        options['download_subtitles'] = input("Download subtitles? (y/n): ").lower().startswith('y')
        options['download_description'] = input("Download description? (y/n): ").lower().startswith('y')
        
        return options
    
    def build_ydl_opts(self, options, info=None):
        """Build yt-dlp options based on user preferences"""
        ydl_opts = {
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'restrictfilenames': True,
        }
        
        # Format selection based on user choice
        download_type = options['type']
        
        if download_type == 1:  # Video + Audio merged
            quality_map = {
                1: 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
                2: 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
                3: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                4: 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                5: 'bestvideo[height<=480]+bestaudio/best[height<=480]',
                6: 'bestvideo[height<=360]+bestaudio/best[height<=360]',
                7: 'bestvideo+bestaudio/best',
                8: 'worstvideo+worstaudio/worst'
            }
            ydl_opts['format'] = quality_map.get(options.get('quality', 7))
            
            # Output format
            format_map = {1: 'mp4', 2: 'mkv', 3: 'webm', 4: 'avi'}
            if options.get('format'):
                ydl_opts['merge_output_format'] = format_map[options['format']]
        
        elif download_type == 2:  # Video only
            quality_map = {
                1: 'bestvideo[height<=2160]',
                2: 'bestvideo[height<=1440]',
                3: 'bestvideo[height<=1080]',
                4: 'bestvideo[height<=720]',
                5: 'bestvideo[height<=480]',
                6: 'bestvideo[height<=360]',
                7: 'bestvideo',
                8: 'worstvideo'
            }
            ydl_opts['format'] = quality_map.get(options.get('quality', 7))
        
        elif download_type == 3:  # Audio only
            audio_quality_map = {
                1: 'bestaudio',
                2: 'bestaudio[abr<=320]',
                3: 'bestaudio[abr<=256]',
                4: 'bestaudio[abr<=192]',
                5: 'bestaudio[abr<=128]',
                6: 'bestaudio[abr<=96]'
            }
            ydl_opts['format'] = audio_quality_map.get(options.get('audio_quality', 1))
            
            # Audio format
            audio_format_map = {1: 'mp3', 2: 'm4a', 3: 'flac', 4: 'wav', 5: 'ogg'}
            if options.get('audio_format'):
                ext = audio_format_map[options['audio_format']]
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': ext,
                }]
        
        elif download_type == 4:  # Best quality
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        
        elif download_type == 5:  # Worst quality
            ydl_opts['format'] = 'worstvideo+worstaudio/worst'
        
        # Additional options
        if options.get('download_thumbnail'):
            ydl_opts['writethumbnail'] = True
        
        if options.get('download_subtitles'):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['en', 'en-US']
        
        if options.get('download_description'):
            ydl_opts['writedescription'] = True
        
        return ydl_opts
    
    def download_video(self, url, ydl_opts):
        """Download video with progress tracking"""
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', 'N/A')
                speed = d.get('_speed_str', 'N/A')
                print(f"\rDownloading... {percent} at {speed}", end='', flush=True)
            elif d['status'] == 'finished':
                print(f"\n✅ Download completed: {d['filename']}")
        
        ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\n🚀 Starting download...")
                ydl.download([url])
                print("✅ All downloads completed successfully!")
                return True
        except Exception as e:
            print(f"\n❌ Error during download: {str(e)}")
            return False
    
    def run(self):
        """Main application loop"""
        print("="*80)
        print(" 🎬 YOUTUBE DOWNLOADER - Powered by yt-dlp")
        print("="*80)
        
        while True:
            try:
                # Get URL from user
                print("\n" + "-"*60)
                url = input("Enter YouTube URL (or 'quit' to exit): ").strip()
                
                if url.lower() in ['quit', 'q', 'exit']:
                    print("👋 Thanks for using YouTube Downloader!")
                    break
                
                if not url:
                    print("❌ Please enter a valid URL")
                    continue
                
                # Get video information
                print("\n🔍 Fetching video information...")
                info = self.get_video_info(url)
                if not info:
                    print("❌ Could not retrieve video information. Please check the URL.")
                    continue
                
                # Display video info
                self.display_video_info(info)
                
                # Ask if user wants to see available formats
                show_formats = input("\nDo you want to see available formats? (y/n): ").lower().startswith('y')
                if show_formats:
                    video_formats, audio_formats, combined_formats = self.get_available_formats(info)
                    self.display_formats(video_formats, audio_formats, combined_formats)
                
                # Get download preferences
                options = self.get_download_options()
                
                # Build yt-dlp options
                ydl_opts = self.build_ydl_opts(options, info)
                
                # Confirm download
                print(f"\n📁 Files will be saved to: {os.path.abspath(self.download_path)}")
                confirm = input("Proceed with download? (y/n): ").lower().startswith('y')
                
                if confirm:
                    success = self.download_video(url, ydl_opts)
                    if success:
                        print(f"📁 Check your downloads folder: {os.path.abspath(self.download_path)}")
                else:
                    print("❌ Download cancelled.")
                
                # Ask if user wants to download another video
                another = input("\nDownload another video? (y/n): ").lower().startswith('y')
                if not another:
                    print("👋 Thanks for using YouTube Downloader!")
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                continue

def main():
    """Entry point of the application"""
    # Check if yt-dlp is installed
    try:
        import yt_dlp
    except ImportError:
        print("❌ yt-dlp is not installed!")
        print("Please install it using: pip install yt-dlp")
        sys.exit(1)
    
    # Create and run the downloader
    downloader = YouTubeDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
