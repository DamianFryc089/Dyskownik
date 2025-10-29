class ConfigData:
	def __init__(self, config_dict):
		self.logger_level = config_dict.get('LOGGER_LEVEL', 'INFO').upper()
		self.database_file = config_dict.get('DATABASE_FILE', 'drive_index.db')
		self.skip_heavy_tests = config_dict.get('SKIP_HEAVY_TESTS', 'False').lower() in ('true', '1', 'yes')
		self.test_drive_folder_id = config_dict.get('TEST_DRIVE_FOLDER_ID', '')
		self.log_file = config_dict.get('LOG_FILE', 'logs/dyskownik.log')
