from src import utils
from src.db.query_options import FileQueryOptions
from src.drive.drive_builder import DriveBuilder
from src.models.drive_file import DriveFile
from src.models.file import File
from src.models.category import Category
from src.models.category_type import CategoryType
from src.models.category_alias import CategoryAlias
from main import logger


class UpdateService:

	@staticmethod
	def data_update(new_file_with_data: str):
		logger.info(f"Starting database update with file: {new_file_with_data}")

		files_data = utils.get_json(new_file_with_data)
		if files_data is None or not isinstance(files_data, list):
			logger.error(f"Failed to load data from {new_file_with_data}. Invalid format.")
			return

		added_files_count = File.add_batch(files_data, FileQueryOptions(temp=True))
		if added_files_count is None:
			logger.error("Failed to add files to temporary storage.")
			return

		category_types = CategoryType.get_all()
		for category_type in category_types:
			category_type.link_all_files(temp=True)
		logger.debug("Linked files to categories in temporary storage.")

		Category.replace_links()
		File.replace_files()
		logger.debug("Replaced temporary files and links with permanent ones.")

		logger.info(f"Added {added_files_count} files to the database.")
		logger.info("Database update completed successfully.")

	@staticmethod
	def drive_update_all(drive_builder: DriveBuilder = None):
		"""
		Updates Google Drive structure based on current database state.
		"""
		drive_builder = drive_builder or DriveBuilder()
		category_types = CategoryType.get_all()
		for category_type in category_types:
			drive_builder.build_category_type_normal(category_type)

		# Remove obsolete category type folders from drive_file table
		for category_type_drive in DriveFile.get_drive_files_by_level(1):
			if category_type_drive.category_type_id not in [ct.id for ct in category_types]:
				category_type_drive.delete()
				logger.debug(f"Deleted obsolete category type folder with ID {category_type_drive.drive_file_id} from drive_file table.")

		# Remove obsolete category folders and shortcuts from drive_file table
		for category_type in category_types:
			categories = Category.get_by_type(category_type)
			for category_drive in DriveFile.get_drive_files_by_level(2, category_type):
				if category_drive.name not in [c.canonical_name for c in categories]:
					category_drive.delete()
					logger.debug(f"Deleted obsolete category folder '{category_drive.name}' with ID {category_drive.drive_file_id} from drive_file table.")

			for category in categories:
				files = File.get_from_category(category, FileQueryOptions(exclude_shortcuts=False))
				category_drive = next((cd for cd in DriveFile.get_drive_files_by_level(2, category_type) if
									   cd.name == category.canonical_name), None)
				if category_drive is None:
					continue
				for file_drive in DriveFile.get_drive_files_by_level(3, category_type, category_drive.drive_file_id):
					if file_drive.shortcut_target_id not in [f.drive_file_id for f in files]:
						file_drive.delete()
						logger.debug(f"Deleted obsolete shortcut '{file_drive.name}' with ID {file_drive.drive_file_id} from drive_file table.")

		drive_builder.remove_old_files()
		logger.info("Google Drive structure update completed successfully.")
