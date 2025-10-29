import time

from main import logger
from src.commands.db_commands import update_data_in_database
from src.commands.drive_commands import drive_update, drive_fetch_data


class ServerService:
	def __init__(self, main_folders_file: str = "auto_main_folders.txt", scan_file: str = "auto_scan.json"):
		self.main_folders_file = main_folders_file
		self.scan_file = scan_file

	def start_server(self, scan_interval: int):
		"""
		Starts a server that periodically fetches data from Google Drive and updates the database.
		:param scan_interval: Interval in seconds between scans.
		:return:
		"""
		logger.info("Server started")
		try:
			while True:
				drive_fetch_data(type('Args', (object,), {
					'start_folders_file': self.main_folders_file,
					'json_file': self.scan_file,
					'max_workers': 10,
					'save_every_files': 10000000,
					'search_parent': True
				})())
				update_data_in_database(args=type('Args', (object,), {
					'file_with_data': self.scan_file
				})())
				drive_update(None)
				time.sleep(scan_interval)
		except KeyboardInterrupt:
			logger.info("Server stopping due to KeyboardInterrupt")
		except Exception as e:
			logger.error(f"Error in server loop: {e}")
