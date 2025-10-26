# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""YouTube downloader service using yt-dlp for video/audio downloads.

Provides asynchronous YouTube video download functionality with real-time
progress tracking, chapter processing, and file organization. Handles both
single videos and playlists with proper error handling and notifications.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict

import yt_dlp
import logging

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """Downloader service for handling YouTube video/audio downloads using yt-dlp."""

    def __init__(self, upload_folder: str, progress_callback: Callable = None):
        self.upload_folder = Path(upload_folder)
        self.progress_callback = progress_callback
        self._last_reported_percentage = -1  # Renamed and initialized for better tracking
        self.main_loop = None  # Will store the main asyncio event loop

    # MARK: - Progress Handling
    def _handle_progress(self, progress: dict):
        if progress["status"] == "error":
            logger.error(
                f"yt-dlp reported an error during download: {progress.get('error')}"
            )
            if self.progress_callback and self.main_loop:
                error_data = {
                    "status": "error",  # Generic error status
                    "message": f"Download error: {progress.get('error', 'Unknown error from yt-dlp')}",
                    "details": progress,
                    "phase": "download",
                }
                try:
                    coro = self.progress_callback(error_data)
                    asyncio.run_coroutine_threadsafe(coro, self.main_loop)
                except Exception as e:
                    logger.error(
                        f"Error sending download error notification: {e}"
                    )
            return

        # We are interested in 'downloading' for percentage, and 'finished' to
        # ensure 100% is marked.
        if progress["status"] not in ["downloading", "finished"]:
            logger.debug(
                f"Progress hook called with status: {progress['status']} - ignoring for percentage."
            )
            return

        total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        downloaded_bytes = progress.get("downloaded_bytes", 0)

        if total is None or total == 0:  # total can be None initially
            if (
                downloaded_bytes == 0 and self._last_reported_percentage < 0
            ):  # Send initial 0% if not yet sent
                percentage = 0
            else:  # Not enough info to calculate percentage reliably yet
                logger.debug(f"Progress hook: Not enough data for percentage (total: {total}, downloaded: {downloaded_bytes})",
                )
                return
        else:
            percentage = int((downloaded_bytes / total) * 100)

        percentage = max(0, min(100, percentage))  # Clamp percentage

        logger.debug(
            f"Raw download progress: {percentage}% ({downloaded_bytes}/{total or 'N/A'} bytes), status: {progress['status']}"
        )

        # Send update if percentage increased, or if it's 100% and not yet
        # reported, or initial 0%
        if (
            percentage > self._last_reported_percentage
            or (percentage == 100 and self._last_reported_percentage < 100)
            or (percentage == 0 and self._last_reported_percentage < 0 and downloaded_bytes == 0)
        ):

            # If yt-dlp reports 'finished' for the download part, ensure we send 100%
            if progress["status"] == "finished" and percentage < 100:
                logger.debug(
                    f"Download status is 'finished' but percentage is {percentage}%. Forcing to 100%."
                )
                percentage = 100
                if total:
                    downloaded_bytes = total  # Assume full download if total is known

            self._last_reported_percentage = percentage

            if self.progress_callback and self.main_loop:
                progress_data = {
                    "status": "download_in_progress",  # Specific status for per-percentage updates
                    "progress": percentage,
                    "downloaded_bytes": downloaded_bytes,
                    "total_bytes": total,
                    "message": f"Downloading: {percentage}%",
                }
                try:
                    coro = self.progress_callback(progress_data)
                    asyncio.run_coroutine_threadsafe(coro, self.main_loop)
                    logger.debug(
                        f"Sent download_in_progress notification: {percentage}%"
                    )
                except Exception as e:
                    logger.error(
                        f"Error sending download_in_progress notification: {e}"
                    )

    # MARK: - Post-processor Progress Handling
    def _handle_postprocessor_progress(self, pp_info: dict):
        logger.debug(f"Post-processor hook: {pp_info}")
        if not self.progress_callback or not self.main_loop:
            return

        status_map = {
            "started": "post_processing_started",
            "finished": "post_processing_finished",
            "error": "post_processing_error",  # Handle errors from post-processors
        }

        current_status = pp_info.get("status")
        postprocessor_name = pp_info.get("postprocessor")

        if current_status in status_map:
            event_status = status_map[current_status]
            message = f"Post-processing ({postprocessor_name}): {current_status}"
            if current_status == "error":
                message = f"Error during post-processing ({postprocessor_name}): {pp_info.get('msg', 'Unknown error')}"

            # Ensure 100% download message is sent before post-processing starts
            if event_status == "post_processing_started" and self._last_reported_percentage < 100:
                logger.debug(
                    "Ensuring 100% download notification before post-processing starts."
                )
                download_complete_data = {
                    "status": "download_in_progress",
                    "progress": 100,
                    "message": "Download 100% complete, starting post-processing...",
                    # downloaded_bytes and total_bytes can be omitted or fetched if
                    # available
                }
                try:
                    coro_dl_complete = self.progress_callback(download_complete_data)
                    asyncio.run_coroutine_threadsafe(coro_dl_complete, self.main_loop)
                    self._last_reported_percentage = 100  # Mark download as 100%
                except Exception as e:
                    logger.error(
                        f"Error sending final download progress notification before post-processing: {e}"
                    )

            progress_data = {
                "status": event_status,
                "message": message,
                "postprocessor": postprocessor_name,
            }
            if current_status == "error":
                progress_data["error_details"] = pp_info.get("msg")

            try:
                coro = self.progress_callback(progress_data)
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)
                logger.debug(
                    f"Sent post-processing notification: {event_status} for {postprocessor_name}"
                )
            except Exception as e:
                logger.error(f"Error sending post-processing notification: {e}")

    # MARK: - Download Core Logic
    def _perform_download_blocking(self, url: str, playlist_folder: Path) -> Dict[str, Any]:
        """Perform the actual blocking download operation.

        This method is intended to be run in a separate thread.
        """
        try:
            # Notify that we're starting the download process
            if self.progress_callback and self.main_loop:
                coro = self.progress_callback(
                    {
                        "status": "download_started",
                        "progress": 0,
                        "message": "Starting download process...",
                    }
                )
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)

            # Extract info first without downloading
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            # Create safe folder name from title
            safe_title = "".join(
                [c if c.isalnum() or c in " -_" else "_" for c in info.get("title", "Unknown")]
            )

            # Define the folder where individual files will be stored
            # Ensure playlist_folder is absolute to avoid issues with yt-dlp's path
            # handling
            abs_playlist_folder = playlist_folder.resolve()
            files_output_folder = abs_playlist_folder / "files"
            files_output_folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured output subfolder exists: {files_output_folder}",
            )

            # Notify that we're preparing to download
            if self.progress_callback and self.main_loop:
                # Reset last reported percentage for the new download operation
                self._last_reported_percentage = -1
                coro = self.progress_callback(
                    {
                        "status": "download_preparing",
                        "progress": 0,  # Initial progress
                        "message": "Preparing download options...",
                    }
                )
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)

            # Create download options
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                    }
                ],
                # Save to 'files' subdirectory
                "outtmpl": str(files_output_folder / "%(title)s.%(ext)s"),
                "split_chapters": True,
                # 'paths': {'home': str(abs_playlist_folder)}, # Not strictly needed if outtmpl is absolute
                "progress_hooks": [self._handle_progress],
                "postprocessor_hooks": [self._handle_postprocessor_progress],
                "force_overwrites": True,
                "quiet": False,  # Changed to False for more detailed progress from yt-dlp
                "no_warnings": True,
                "logger": None,  # Can be set to `logger` for yt-dlp's internal logs if needed
                "noprogress": False,  # CRITICAL: Changed to False to enable progress events
                "keepvideo": False,
                "ignoreerrors": False,  # Default is False, but good to be explicit for downloads
            }

            # Download with the options
            # This block will trigger _handle_progress and
            # _handle_postprocessor_progress
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # The download=True call is blocking and will run in this thread.
                # Progress hooks are called synchronously by yt-dlp from this thread.
                # Our hooks then use run_coroutine_threadsafe to talk to the main
                # asyncio loop.
                info = ydl.extract_info(url, download=True)

            # Notify that we're starting custom chapter analysis / track preparation
            # This happens AFTER yt-dlp download and its internal post-processing are
            # complete
            if self.progress_callback and self.main_loop:
                coro = self.progress_callback(
                    {
                        "status": "analyzing_chapters",  # Renamed from 'processing_files'
                        "message": "Analyzing chapters and preparing track list...",
                    }
                )
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)

            # Scan the 'files' subfolder for MP3 files
            mp3_files = list(files_output_folder.glob("*.mp3"))
            logger.info(f"Found {len(mp3_files)} MP3 files in {files_output_folder}",
            )

            # Get chapters or build a track list
            chapters = info.get("chapters", [])
            processed_files_info = []

            # If we have MP3 files but no chapters info from yt-dlp, create chapters
            # from the files
            if not chapters and mp3_files:
                # Check if it's a playlist
                entries = info.get("entries", [])
                if entries:
                    logger.debug(f"Playlist '{info.get('title', 'Unknown')}' (ID: {info.get('id', 'Unknown')}): No explicit chapters found. Processing {len(entries)} entries as individual chapters.",
                    )

                    # Try to match entries with files
                    for idx, entry in enumerate(entries, 1):
                        entry_title = entry.get("title", f"Track {idx}")
                        # Try to find a matching file
                        matching_file = next(
                            (f for f in mp3_files if entry_title.lower() in f.stem.lower()),
                            None,
                        )

                        if matching_file:
                            processed_files_info.append(
                                {
                                    "title": entry_title,
                                    "start_time": 0,
                                    "end_time": entry.get("duration", 0),
                                    # Add 'files/' prefix
                                    "filename": str(Path("files") / matching_file.name),
                                }
                            )
                        else:
                            # Fallback if no match found
                            logger.warning(f"Could not find matching file for playlist entry '{entry_title}'. Using entry title as filename basis.",
                            )
                            processed_files_info.append(
                                {
                                    "title": entry_title,
                                    "start_time": 0,
                                    "end_time": entry.get("duration", 0),
                                    # Add 'files/' prefix
                                    "filename": str(Path("files") / f"{entry_title}.mp3"),
                                }
                            )
                else:
                    # Single file - use the actual file we found
                    if mp3_files:
                        processed_files_info.append(
                            {
                                "title": info.get("title", mp3_files[0].stem),
                                "start_time": 0,
                                "end_time": info.get("duration", 0),
                                # Add 'files/' prefix
                                "filename": str(Path("files") / mp3_files[0].name),
                            }
                        )
            elif chapters:
                # We have chapter info from yt-dlp, try to match with actual files
                for idx, chapter in enumerate(
                    chapters, 1
                ):  # Added idx for better fallback filenames
                    chapter_title = chapter.get("title", f"Chapter {idx}")
                    # Try to find a matching file more robustly
                    potential_filename_prefix = f"{idx:03d} - {chapter_title}"

                    matching_file = next(
                        (
                            f
                            for f in mp3_files
                            if (
                                chapter_title.lower() in f.stem.lower()
                                or f.stem.lower().startswith(
                                    potential_filename_prefix.lower()[: len(f.stem)]
                                )
                                or potential_filename_prefix.lower()[:30]
                                in f.stem.lower()  # Match first 30 chars
                            )
                        ),
                        None,
                    )

                    if matching_file:
                        processed_files_info.append(
                            {
                                "title": chapter_title,
                                "start_time": chapter.get("start_time", 0),
                                "end_time": chapter.get("end_time", 0),
                                # Add 'files/' prefix
                                "filename": str(Path("files") / matching_file.name),
                            }
                        )
                    else:
                        logger.warning(f"Could not find matching file for chapter '{chapter_title}'. Using chapter title as filename basis: {str(Path('files') / f'{chapter_title}.mp3')}",
                        )
                        processed_files_info.append(
                            {
                                "title": chapter_title,
                                "start_time": chapter.get("start_time", 0),
                                "end_time": chapter.get("end_time", 0),
                                # Add 'files/' prefix
                                "filename": str(Path("files") / f"{chapter_title}.mp3"),
                            }
                        )
            else:
                # No chapters and no files found - this shouldn't happen but handle it
                # anyway
                logger.warning(f"No chapters or MP3 files found for {url}")
                processed_files_info = []

            # If we still have no processed files but have MP3 files, create entries
            # for each file
            if not processed_files_info and mp3_files:
                for idx, file_path in enumerate(sorted(mp3_files), 1):
                    processed_files_info.append(
                        {
                            "title": file_path.stem,
                            "start_time": 0,
                            "end_time": 0,  # We don't know the duration
                            # Add 'files/' prefix
                            "filename": str(Path("files") / file_path.name),
                        }
                    )

            # Notify that custom chapter/track processing is complete
            if self.progress_callback and self.main_loop:
                coro = self.progress_callback(
                    {
                        "status": "files_processed",
                        "message": f"Track analysis complete. Found {len(processed_files_info)} tracks.",
                    }
                )
                asyncio.run_coroutine_threadsafe(coro, self.main_loop)

            return {
                "title": info.get("title", "Unknown"),
                "id": info.get("id", "Unknown"),
                "folder": safe_title,  # Return the relative folder name
                "chapters": processed_files_info,  # Use our processed files info
            }
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            # Ensure any exception here is also reported via progress callback if
            # possible
            if self.progress_callback and self.main_loop:
                error_data = {
                    "status": "error",
                    "message": f"An unexpected error occurred: {str(e)}",
                    "details": str(e),  # Keep it simple for now
                    "phase": "download_core",
                }
                try:
                    # Use run_coroutine_threadsafe as this is a blocking method
                    asyncio.run_coroutine_threadsafe(
                        self.progress_callback(error_data), self.main_loop
                    )
                except Exception as cb_e:
                    logger.error(f"Error sending final error notification: {cb_e}",
                    )
            raise

    async def download(self, url: str) -> Dict[str, Any]:
        """Asynchronous method to download a YouTube video.

        This method captures the current event loop and runs the
        blocking download operation in a separate thread to avoid
        blocking the asyncio event loop.
        """
        try:
            # Capture the current event loop for use in progress callbacks
            self.main_loop = asyncio.get_running_loop()

            # Extract initial info to get the title (without downloading)
            # This is quick and non-blocking enough for an async context usually
            with yt_dlp.YoutubeDL(
                {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
            ) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)

            # Create a safe folder name from the title
            safe_title = "".join(
                [c if c.isalnum() or c in " -_" else "_" for c in info.get("title", "Unknown")]
            )
            playlist_folder = self.upload_folder / safe_title

            # Create the folder if it doesn't exist (idempotent)
            playlist_folder.mkdir(exist_ok=True)

            # Run the blocking download operation in a separate thread
            result = await asyncio.to_thread(
                self._perform_download_blocking,
                url,
                playlist_folder,  # Pass the base playlist folder
            )

            return result

        except Exception as e:
            logger.error(f"Async download failed: {str(e)}")
            # Ensure any exception here is also reported via progress callback if possible
            # This is tricky if main_loop or progress_callback isn't set up yet or if
            # the error is in setup
            if (
                hasattr(self, "progress_callback")
                and self.progress_callback
                and hasattr(self, "main_loop")
                and self.main_loop
            ):
                error_data = {
                    "status": "error",
                    "message": f"An unexpected error occurred in async download: {str(e)}",
                    "details": str(e),
                    "phase": "async_setup",
                }
                try:
                    # This is an async context, so we can await directly if callback is async
                    # However, progress_callback is designed to be called from sync thread.
                    # For consistency, and if this part can be reached before main_loop is set by _perform_download_blocking
                    # it's safer to check. But here, main_loop should be set.
                    # Assuming progress_callback is async
                    await self.progress_callback(error_data)
                except Exception as cb_e:
                    logger.error(f"Error sending async error notification: {cb_e}",
                    )
            raise
