import time

from main import logger
from src.commands.db_commands import update_data_in_database
from src.commands.drive_commands import drive_update, drive_fetch_data


class ServerService:
	main_folders_file : str = "auto_main_folders.txt"
	scan_file : str = "auto_scan.json"
	max_workers : int = 10
	save_every_files : int = 10000000
	search_parent : bool = False

	def start_server(self, scan_interval: int):
		"""
		Starts a server that periodically fetches data from Google Drive and updates the database.
		:param scan_interval: Interval in seconds between scans.
		:return:
		"""
		logger.info("Server started")
		try:
			while True:
				scan_result = drive_fetch_data(type('Args', (object,), {
					'start_folders_file': self.main_folders_file,
					'json_file': self.scan_file,
					'max_workers': self.max_workers,
					'save_every_files': self.save_every_files,
					'search_parent': self.search_parent
				})())
				if scan_result:
					update_data_in_database(args=type('Args', (object,), {
						'file_with_data': self.scan_file
					})())
					drive_update(None)
				time.sleep(scan_interval)
		except KeyboardInterrupt:
			logger.info("Server stopping due to KeyboardInterrupt")
		except Exception as e:
			logger.error(f"Error in server loop: {e}")
