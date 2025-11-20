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
            self._notify_download_started()
            info = self._extract_video_info(url)
            safe_title, files_output_folder = self._prepare_output_folders(playlist_folder, info)

            self._notify_download_preparing()
            ydl_opts = self._create_download_options(files_output_folder)

            info = self._perform_download(url, ydl_opts)

            self._notify_analyzing_chapters()
            mp3_files = self._scan_mp3_files(files_output_folder)
            processed_files_info = self._process_tracks_and_chapters(info, mp3_files)

            self._notify_files_processed(processed_files_info)

            return {
                "title": info.get("title", "Unknown"),
                "id": info.get("id", "Unknown"),
                "folder": safe_title,
                "chapters": processed_files_info,
            }
        except Exception as e:
            self._handle_download_error(e)
            raise

    def _notify_download_started(self) -> None:
        """Notify that download process is starting."""
        if self.progress_callback and self.main_loop:
            coro = self.progress_callback({
                "status": "download_started",
                "progress": 0,
                "message": "Starting download process...",
            })
            asyncio.run_coroutine_threadsafe(coro, self.main_loop)

    def _extract_video_info(self, url: str) -> Dict[str, Any]:
        """Extract video information without downloading."""
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            return ydl.extract_info(url, download=False)

    def _prepare_output_folders(self, playlist_folder: Path, info: Dict[str, Any]) -> tuple[str, Path]:
        """Prepare output folders for download."""
        safe_title = "".join([
            c if c.isalnum() or c in " -_" else "_"
            for c in info.get("title", "Unknown")
        ])

        abs_playlist_folder = playlist_folder.resolve()
        files_output_folder = abs_playlist_folder / "files"
        files_output_folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured output subfolder exists: {files_output_folder}")

        return safe_title, files_output_folder

    def _notify_download_preparing(self) -> None:
        """Notify that download preparation is starting."""
        if self.progress_callback and self.main_loop:
            self._last_reported_percentage = -1
            coro = self.progress_callback({
                "status": "download_preparing",
                "progress": 0,
                "message": "Preparing download options...",
            })
            asyncio.run_coroutine_threadsafe(coro, self.main_loop)

    def _create_download_options(self, files_output_folder: Path) -> Dict[str, Any]:
        """Create yt-dlp download options."""
        return {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            "outtmpl": str(files_output_folder / "%(title)s.%(ext)s"),
            "split_chapters": True,
            "progress_hooks": [self._handle_progress],
            "postprocessor_hooks": [self._handle_postprocessor_progress],
            "force_overwrites": True,
            "quiet": False,
            "no_warnings": True,
            "logger": None,
            "noprogress": False,
            "keepvideo": False,
            "ignoreerrors": False,
        }

    def _perform_download(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual download using yt-dlp."""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    def _notify_analyzing_chapters(self) -> None:
        """Notify that chapter analysis is starting."""
        if self.progress_callback and self.main_loop:
            coro = self.progress_callback({
                "status": "analyzing_chapters",
                "message": "Analyzing chapters and preparing track list...",
            })
            asyncio.run_coroutine_threadsafe(coro, self.main_loop)

    def _scan_mp3_files(self, files_output_folder: Path) -> list:
        """Scan for MP3 files in the output folder."""
        mp3_files = list(files_output_folder.glob("*.mp3"))
        logger.info(f"Found {len(mp3_files)} MP3 files in {files_output_folder}")
        return mp3_files

    def _process_tracks_and_chapters(
        self, info: Dict[str, Any], mp3_files: list
    ) -> list[Dict[str, Any]]:
        """Process tracks and chapters from download info."""
        chapters = info.get("chapters", [])

        if not chapters and mp3_files:
            return self._process_without_chapters(info, mp3_files)
        elif chapters:
            return self._process_with_chapters(chapters, mp3_files)
        else:
            logger.warning(f"No chapters or MP3 files found for {info.get('id', 'Unknown')}")
            return self._process_fallback_tracks(mp3_files)

    def _process_without_chapters(
        self, info: Dict[str, Any], mp3_files: list
    ) -> list[Dict[str, Any]]:
        """Process tracks when no chapter information is available."""
        entries = info.get("entries", [])

        if entries:
            return self._process_playlist_entries(info, entries, mp3_files)
        else:
            return self._process_single_file(info, mp3_files)

    def _process_playlist_entries(
        self, info: Dict[str, Any], entries: list, mp3_files: list
    ) -> list[Dict[str, Any]]:
        """Process playlist entries and match with files."""
        logger.debug(
            f"Playlist '{info.get('title', 'Unknown')}' (ID: {info.get('id', 'Unknown')}): "
            f"No explicit chapters found. Processing {len(entries)} entries as individual chapters."
        )

        processed_files_info = []
        for idx, entry in enumerate(entries, 1):
            entry_title = entry.get("title", f"Track {idx}")
            matching_file = next(
                (f for f in mp3_files if entry_title.lower() in f.stem.lower()),
                None
            )

            if matching_file:
                filename = str(Path("files") / matching_file.name)
            else:
                logger.warning(
                    f"Could not find matching file for playlist entry '{entry_title}'. "
                    f"Using entry title as filename basis."
                )
                filename = str(Path("files") / f"{entry_title}.mp3")

            processed_files_info.append({
                "title": entry_title,
                "start_time": 0,
                "end_time": entry.get("duration", 0),
                "filename": filename,
            })

        return processed_files_info

    def _process_single_file(
        self, info: Dict[str, Any], mp3_files: list
    ) -> list[Dict[str, Any]]:
        """Process a single file download."""
        if not mp3_files:
            return []

        return [{
            "title": info.get("title", mp3_files[0].stem),
            "start_time": 0,
            "end_time": info.get("duration", 0),
            "filename": str(Path("files") / mp3_files[0].name),
        }]

    def _process_with_chapters(
        self, chapters: list, mp3_files: list
    ) -> list[Dict[str, Any]]:
        """Process download with chapter information."""
        processed_files_info = []

        for idx, chapter in enumerate(chapters, 1):
            chapter_title = chapter.get("title", f"Chapter {idx}")
            matching_file = self._find_matching_chapter_file(chapter_title, idx, mp3_files)

            if matching_file:
                filename = str(Path("files") / matching_file.name)
            else:
                logger.warning(
                    f"Could not find matching file for chapter '{chapter_title}'. "
                    f"Using chapter title as filename basis: "
                    f"{str(Path('files') / f'{chapter_title}.mp3')}"
                )
                filename = str(Path("files") / f"{chapter_title}.mp3")

            processed_files_info.append({
                "title": chapter_title,
                "start_time": chapter.get("start_time", 0),
                "end_time": chapter.get("end_time", 0),
                "filename": filename,
            })

        return processed_files_info

    def _find_matching_chapter_file(
        self, chapter_title: str, idx: int, mp3_files: list
    ) -> Path | None:
        """Find matching file for a chapter."""
        potential_filename_prefix = f"{idx:03d} - {chapter_title}"

        return next(
            (
                f for f in mp3_files
                if (
                    chapter_title.lower() in f.stem.lower()
                    or f.stem.lower().startswith(
                        potential_filename_prefix.lower()[:len(f.stem)]
                    )
                    or potential_filename_prefix.lower()[:30] in f.stem.lower()
                )
            ),
            None
        )

    def _process_fallback_tracks(self, mp3_files: list) -> list[Dict[str, Any]]:
        """Process tracks as fallback when no other info is available."""
        if not mp3_files:
            return []

        return [
            {
                "title": file_path.stem,
                "start_time": 0,
                "end_time": 0,
                "filename": str(Path("files") / file_path.name),
            }
            for file_path in sorted(mp3_files)
        ]

    def _notify_files_processed(self, processed_files_info: list) -> None:
        """Notify that file processing is complete."""
        if self.progress_callback and self.main_loop:
            coro = self.progress_callback({
                "status": "files_processed",
                "message": f"Track analysis complete. Found {len(processed_files_info)} tracks.",
            })
            asyncio.run_coroutine_threadsafe(coro, self.main_loop)

    def _handle_download_error(self, error: Exception) -> None:
        """Handle download errors and notify via callback."""
        logger.error(f"Download failed: {str(error)}")

        if self.progress_callback and self.main_loop:
            error_data = {
                "status": "error",
                "message": f"An unexpected error occurred: {str(error)}",
                "details": str(error),
                "phase": "download_core",
            }
            try:
                asyncio.run_coroutine_threadsafe(
                    self.progress_callback(error_data), self.main_loop
                )
            except Exception as cb_e:
                logger.error(f"Error sending final error notification: {cb_e}")

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
