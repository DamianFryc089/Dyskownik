class ConfigData:
	def __init__(self, config_dict):
		# --- Logs and db ---
		self.logger_level = config_dict.get('LOGGER_LEVEL', 'INFO').upper()
		self.database_file = config_dict.get('DATABASE_FILE', 'drive_index.db')
		self.log_file = config_dict.get('LOG_FILE', 'logs/dyskownik.log')

		# --- Tests ---
		self.skip_heavy_tests = str(config_dict.get('SKIP_HEAVY_TESTS', 'False')).lower() in ('true', '1', 'yes')
		self.test_drive_folder_id = config_dict.get('TEST_DRIVE_FOLDER_ID', '')

		# --- Server parameters ---
		self.server_main_folders_file = config_dict.get('SERVER_MAIN_FOLDERS_FILE', 'auto_main_folders.txt')
		self.server_scan_file = config_dict.get('SERVER_SCAN_FILE', 'auto_scan.json')
		self.server_scan_interval = int(config_dict.get('SERVER_SCAN_INTERVAL', 60 * 60 * 24))
		self.server_max_workers = int(config_dict.get('SERVER_MAX_WORKERS', 10))
		self.server_save_every_files = int(config_dict.get('SERVER_SAVE_EVERY_FILES', 10000000))
		self.server_search_parent = str(config_dict.get('SERVER_SEARCH_PARENT', 'False')).lower() in ('true', '1', 'yes')
