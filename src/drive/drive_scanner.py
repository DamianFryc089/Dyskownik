import concurrent.futures  # For ThreadPoolExecutor
import logging
import threading  # For Locks

import googleapiclient
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from main import logger
from src import utils
from src.drive.drive_API_client import DriveAPIClient, DriveScopeMode
from src.models.file import File


# --- DriveScanner Class for Concurrent Operations ---
class DriveScanner:
	def __init__(self, credentials: Credentials = None, max_workers: int = 5,
				 save_every_files: int = 1000000):

		self.api_client = DriveAPIClient()
		self.credentials = credentials if credentials is not None else DriveAPIClient.get_credentials(
			scope_mode=DriveScopeMode.READ_ONLY)
		self.visited_ids = set()
		self.search_parent = True
		self.max_level = 999

		self.files_to_save_buffer = []
		self.save_counter_reset = save_every_files
		self.save_counter = save_every_files
		self.fetch_file_name = "fetched_data.json"

		# --- Synchronization Primitives ---
		self.visited_lock = threading.Lock()  # Protects self.visited_ids
		self.save_buffer_lock = threading.Lock()  # Protects self.files_to_save_buffer and self.save_counter
		self.all_tasks_done_event = threading.Event()  # Signals when all tasks are complete

		# --- Thread Pool Executor ---
		self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
		self.pending_futures_count = 1  # Count of pending futures, initialized to 1 to avoid premature shutdown
		self.pending_futures_lock = threading.Lock()  # Protects self.pending_futures_count

	def scan_folder_task(self, task_service: googleapiclient.discovery.Resource, folder_id: str, level: int) -> None:
		"""
		Internal method to perform folder scanning, executed by a thread from the pool.
		This replaces the old 'scan_folder' logic.
		"""

		if level > self.max_level:
			logger.debug(f"Skipping folder {folder_id} due to MAX_LEVEL reached.")
			return

		page_token = None
		while True:
			response = self.api_client.fetch_folder_data(task_service, folder_id, page_token)
			files_on_page = response.get('files', [])

			if not files_on_page and not response.get('nextPageToken'):
				logger.debug(f"No more files or pages for folder {folder_id}")
				break

			for file in files_on_page:
				self.submit_file_process_task(file, level)

			page_token = response.get('nextPageToken')
			if not page_token:
				break

	def submit_file_process_task(self, file: File, level: int = 0):
		"""
		Submits a folder scanning task to the thread pool.
		Checks for already visited folders before submission.
		"""

		with self.pending_futures_lock:
			self.pending_futures_count += 1
		try:
			self.executor.submit(self.process_file, file, level)
		except Exception as e:
			with self.pending_futures_lock:
				self.pending_futures_count -= 1
			logger.error(f"Failed to submit file process for file {file.drive_file_id}: {e}", exc_info=True)

	def get_file(self, file_id: str, task_service=None) -> File | None:
		if task_service is None:
			task_service = DriveAPIClient.create_drive_service(self.credentials)
			# task_service = build('drive', 'v3', credentials=self.credentials)
		return self.api_client.fetch_file_data(task_service, file_id)

	def get_and_process_file(self, file_id: str, level: int = 0, task_service=None) -> None:
		file = self.get_file(file_id, task_service)
		self.process_file(file, level, task_service)

	def process_file(self, file: File, level: int = 0, task_service=None) -> None:
		"""
		Processes a single file or folder entry, adds it to buffer, and potentially
		submits new scan tasks for folders or shortcut targets.
		"""
		if not file:
			logger.warning("Received empty file data, skipping processing.")
			self.end_task(task_service)
			return

		if task_service is None:
			task_service = DriveAPIClient.create_drive_service(self.credentials)
			# task_service = build('drive', 'v3', credentials=self.credentials)

		with self.visited_lock:
			if file.drive_file_id in self.visited_ids:
				logger.debug(f"Skipping already processed file: {file.name} ({file.drive_file_id})")
				self.end_task(task_service)
				return
			self.visited_ids.add(file.drive_file_id)

		with self.save_buffer_lock:
			self.files_to_save_buffer.append(file)
			self.save_counter -= 1

			if self.save_counter <= 0:
				utils.append_to_json(self.files_to_save_buffer, self.fetch_file_name)
				logger.info(f"Saved {len(self.files_to_save_buffer)} files to {self.fetch_file_name}")
				self.files_to_save_buffer = []
				self.save_counter = self.save_counter_reset

		if self.search_parent and file.parent_id:
			do_scan: bool = True
			with self.visited_lock:
				if file.parent_id in self.visited_ids:
					do_scan = False
			if do_scan:
				# It's like a creating a new task path so we need to increment the task count
				with self.pending_futures_lock:
					self.pending_futures_count += 1
				self.get_and_process_file(file.parent_id, level, task_service)

		if file.mime_type == 'application/vnd.google-apps.folder':
			self.scan_folder_task(task_service, file.drive_file_id, level + 1)
			self.end_task(task_service)
			return

		if file.mime_type == 'application/vnd.google-apps.shortcut':
			self.get_and_process_file(file.shortcut_target_id, level, task_service)
			return

		# If it's a file, so the end of the path
		self.end_task(task_service)

	def end_task(self, task_service):
		with self.pending_futures_lock:
			self.pending_futures_count -= 1
			logger.debug(f"Task completed, pending futures count: {self.pending_futures_count}")
			task_service.close()
			if self.pending_futures_count == 0:
				self.all_tasks_done_event.set()  # Signal that all tasks are done

	def shutdown(self):
		"""Shuts down the thread pool and waits for all tasks to complete."""
		self.all_tasks_done_event.wait()  # Wait for all tasks to signal completion
		self.executor.shutdown(wait=True)  # Ensure all submitted tasks are finished
		logger.info("Thread pool shut down.")


# --- Main Execution Block ---
def run_normal(starting_folders_file: str, json_file: str, max_workers: int, save_every_files: int,
			   search_parent: bool = False) -> bool:
	scanner = None
	try:
		scanner = DriveScanner(max_workers=max_workers, save_every_files=save_every_files)
		scanner.search_parent = search_parent
		scanner.fetch_file_name = json_file

		main_folders: list[str] = utils.get_lines_from_file(starting_folders_file, True)
		if not main_folders:
			logger.warning(f"No drive IDs found in {starting_folders_file}. Exiting.")
			return False

		task_service = DriveAPIClient.create_drive_service(scanner.credentials)
		# task_service = build('drive', 'v3', credentials=scanner.credentials)
		for folder_id in main_folders:
			logger.info(f"Starting scan for drive/folder ID: {folder_id}")
			scanner.get_and_process_file(folder_id, 0, task_service)
		scanner.shutdown()

	except Exception as e:
		logger.critical(f"An unhandled error occurred during execution: {e}", exc_info=True)
		if scanner:
			scanner.executor.shutdown(cancel_futures=True)
		return False
	finally:
		if scanner and scanner.files_to_save_buffer:
			with scanner.save_buffer_lock:
				utils.append_to_json(scanner.files_to_save_buffer, json_file)
				logger.info(f"Saved remaining {len(scanner.files_to_save_buffer)} files to {json_file} on exit.")
		logger.info("Scan process finished.")
	return True


if __name__ == '__main__':
	run_normal('drives.txt', 'import_today.json', max_workers=25, save_every_files=1000, search_parent=True)
