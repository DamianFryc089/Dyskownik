import sqlite3
from enum import Enum


class IntegrityLevel(Enum):
	BASE = 1  # only database existence
	STRUCTURE = 2  # database existence + schema
	CATEGORY_ONLY = 3  # schema + category data
	ROOT_ONLY = 4  # schema + root folder check
	FILES = 5  # only files table check
	FULL = 10  # category and root checks


class DBIntegrityChecker:
	"""Class to check the integrity of the database at various levels."""

	def test_db_integrity(self, level: IntegrityLevel = IntegrityLevel.FULL) -> bool:
		from src.db.database import get_db_connection
		from main import logger
		try:
			# 1. Check if the database file exists and is accessible
			conn = get_db_connection()
			conn.execute("SELECT 1;")
			conn.close()
			if level == IntegrityLevel.BASE:
				return True

			# 2. Check the database schema
			if not self.check_database_schema():
				return False
			if level == IntegrityLevel.STRUCTURE:
				return True

			# 3. Check basic data existence (e.g., categories)
			if level == IntegrityLevel.CATEGORY_ONLY:
				if not self.check_category_types_existence():
					return False
				else:
					return True

			# 4. Check dependent elements, e.g., root folder in Drive
			if level == IntegrityLevel.ROOT_ONLY:
				if not self.check_root_folder_existence():
					return False
				else:
					return True

			# 5. Check files table existence and basic integrity
			if level == IntegrityLevel.FILES:
				if not self.check_files_existence():
					return False
				else:
					return True

			# 10. Full integrity (category + root)
			if not self.check_category_types_existence():
				return False
			if not self.check_root_folder_existence():
				return False

			if level == IntegrityLevel.FULL:
				pass

			return True
		except sqlite3.Error as e:
			logger.error(f"Database not accessible or does not exist: {e}")
			return False

	def check_database_schema(self) -> bool:
		"""Checks whether the database contains the required tables."""
		from src.db.database import get_db_connection
		from main import logger
		required_tables = {
			'files', 'category_types', 'categories', 'category_aliases',
			'file_categories', 'files_temp', 'file_categories_temp', 'drive_files'
		}
		try:
			conn = get_db_connection()
			c = conn.cursor()
			c.execute("SELECT name FROM sqlite_master WHERE type='table';")
			existing_tables = {row[0] for row in c.fetchall()}

			missing_tables = required_tables - existing_tables
			if missing_tables:
				logger.error(f"Missing tables in database: {missing_tables}, try initializing the database again.")
				return False
			return True
		except sqlite3.Error as e:
			logger.error(f"Error while checking database schema: {e}")
			return False

	def check_files_existence(self) -> bool:
		"""Checks whether there is at least one file in the files table."""
		from src.models import File
		from main import logger
		try:
			files = File.get_all()
			if not files:
				logger.error("No files found in the database. Please load file data into the database.")
				return False
			return True
		except sqlite3.Error as e:
			logger.error(f"Error while checking files existence: {e}")
			return False

	def check_category_types_existence(self) -> bool:
		"""Checks whether there is at least one category type in the database."""
		from src.models.category_type import CategoryType
		from main import logger
		try:
			category_types = CategoryType.get_all()
			if not category_types:
				logger.error("No category types found in the database.")
				return False
			return True
		except Exception as e:
			logger.error(f"Error while checking category types existence: {e}")
			return False

	def check_root_folder_existence(self) -> bool:
		"""Checks whether a root folder (level 0) exists in the database."""
		from src.models.drive_file import DriveFile
		from main import logger
		try:
			root_folders = DriveFile.get_drive_files_by_level(0)
			if not root_folders:
				logger.error(
					"No root folder found. First set or create a root folder using 'set-root-folder' or 'create-root-folder' command.")
				return False
			return True
		except Exception as e:
			logger.error(f"Error while checking root folder existence: {e}")
			return False
