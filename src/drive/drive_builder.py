import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from main import logger
from src.db.query_options import FileQueryOptions
from src.drive.drive_API_client import DriveAPIClient, DriveScopeMode
from src.models.category import Category
from src.models.category_type import CategoryType
from src.models.drive_file import DriveFile
from src.models.file import File


# --- DriveScanner Class for Concurrent Operations ---
class DriveBuilder:
	def __init__(self):

		self.api_client = DriveAPIClient()
		self.credentials = DriveAPIClient.get_credentials(scope_mode=DriveScopeMode.DRIVE)
		self.service = build('drive', 'v3', credentials=self.credentials)
		self.root_folder_id = DriveFile.get_drive_files_by_level(0)[
			0].drive_file_id if DriveFile.get_drive_files_by_level(0) else None

	def create_root_folder(self, root_folder_name: str, root_folder_location: str = "") -> str | None:
		"""
		Clears all entries in drive_file table
		Creates a root folder in Google Drive if it doesn't already exist.
		Returns the ID of the root folder.
		"""

		task_service = DriveAPIClient.create_drive_service(self.credentials)
		# task_service = build('drive', 'v3', credentials=self.credentials)
		root_folder = self.api_client.create_drive_folder(task_service, root_folder_name, root_folder_location)
		if not root_folder:
			logger.debug(f"Root folder creation failed for name: {root_folder_name}, location: {root_folder_location}")
			return None
		DriveFile.add_drive_file(root_folder, 0)

		self.root_folder_id = root_folder.drive_file_id
		task_service.close()
		return self.root_folder_id

	def get_folder_files(self, folder_id: str, folder_only: bool = False) -> list[File]:
		"""
		Retrieves a list of folders in the folder.
		Returns a list of dictionaries containing folder metadata.
		"""
		task_service = DriveAPIClient.create_drive_service(self.credentials)
		# task_service = build('drive', 'v3', credentials=self.credentials)
		response = self.api_client.fetch_folder_data(task_service, folder_id, None)
		files_on_page: list[File] = response.get('files', [])

		files = []
		for file in files_on_page:
			if folder_only and file.mime_type != 'application/vnd.google-apps.folder':
				continue
			files.append(file)
		task_service.close()
		return files

	def build_category_type_normal(self, category_type: CategoryType):
		"""
		Builds categories and shortcuts for a given category type.
		Creates folders and shortcuts only if they do not exist in drive_file table.
		:param category_type:
		:return:
		"""
		task_service = DriveAPIClient.create_drive_service(self.credentials)
		# task_service = build('drive', 'v3', credentials=self.credentials)

		existing_category_type_folder = DriveFile.get_drive_files_by_level(1, category_type)
		category_type_folder_id = existing_category_type_folder[
			0].drive_file_id if existing_category_type_folder else None

		# Create category type folder if it doesn't exist
		if not category_type_folder_id:
			category_type_folder = self.api_client.create_drive_folder(task_service, category_type.name,
																	   self.root_folder_id)
			if not category_type_folder:
				logger.error(f"Failed to create folder for category '{category_type.name}'")
				return
			DriveFile.add_drive_file(category_type_folder, 1, category_type)
			logger.debug(f"Created category type folder '{category_type.name}' with ID {category_type_folder.drive_file_id}")
			category_type_folder_id = category_type_folder.drive_file_id

		categories = Category.get_by_type(category_type)
		if not categories:
			logger.error(f"No categories found for type '{category_type.name}'")
			return

		for ca in categories:
			query_options = FileQueryOptions(exclude_shortcuts=True,
											 folder_only=category_type.aggregation_type == "shortcut")
			files = File.get_from_category(ca, query_options)
			self.add_shortcuts_normal(task_service, files, category_type, ca, category_type_folder_id)

		task_service.close()

	def add_shortcuts_normal(self, task_service, files: list[File], category_type: CategoryType, category: Category,
							 category_type_folder_id: str):

		# If aggregation type is "shortcut" and there's only one file, create a shortcut directly in the category type folder
		if category_type.aggregation_type == "shortcut" and files.__len__() == 1:  # one file check can be redundant

			existing_shortcuts = DriveFile.get_drive_files_by_level(2, category_type)
			if files[0].drive_file_id in [f.shortcut_target_id for f in existing_shortcuts]:
				return

			shortcut = self.api_client.create_drive_shortcut(task_service, category.canonical_name,
															 files[0].drive_file_id,
															 category_type_folder_id)
			if not shortcut:
				logger.error(f"Failed to create shortcut for category '{category.canonical_name}'")
				return
			logger.debug(f"Creating shortcut '{category.canonical_name}' with ID {category_type_folder_id}'")
			DriveFile.add_drive_file(shortcut, 2, category_type)
			return

		existing_category_folders = DriveFile.get_drive_files_by_level(2, category_type)
		category_folder_id = next(
			(f.drive_file_id for f in existing_category_folders if f.name == category.canonical_name), None)
		# Create category folder if it doesn't exist
		if not category_folder_id:
			category_folder = self.api_client.create_drive_folder(task_service, category.canonical_name,
																  category_type_folder_id)
			if not category_folder:
				logger.error(
					f"Failed to create folder {category.canonical_name} in targeted ID - {category_folder.drive_file_id}")
				return
			logger.debug(f"Created category folder '{category.canonical_name}' with ID {category_folder.drive_file_id}")
			DriveFile.add_drive_file(category_folder, 2, category_type)
			category_folder_id = category_folder.drive_file_id

		existing_shortcuts = DriveFile.get_drive_files_by_level(3, category_type, category_folder_id)
		for file in files:
			if file.drive_file_id in [f.shortcut_target_id for f in existing_shortcuts]:
				continue

			# Create shortcut if it doesn't exist
			shortcut_name = file.name + " (" + file.get_created_date() + ")" if file.mime_type == "application/vnd.google-apps.folder" else file.name
			shortcut = self.api_client.create_drive_shortcut(task_service, shortcut_name,
															 file.drive_file_id if file.shortcut_target_id is None else file.shortcut_target_id,
															 category_folder_id)
			if not shortcut:
				logger.error(f"Failed to create shortcut for file {file.name} in category '{category.canonical_name}'")
				continue
			logger.debug(f"Creating shortcut '{shortcut_name}' in category '{category.canonical_name}' with ID {shortcut.drive_file_id}'")
			DriveFile.add_drive_file(shortcut, 3, category_type)

	def remove_old_files(self) -> bool:
		"""
		Removes old files and folders from Google Drive that are not present in drive_file table.
		Deletes data in the following order: category_type_folder -> category_folder -> shortcuts.
		"""
		task_service = DriveAPIClient.create_drive_service(self.credentials)
		# task_service = build('drive', 'v3', credentials=self.credentials)

		all_files = DriveFile.get_all_drive_files()
		drive_category_type_folders = self.get_folder_files(self.root_folder_id, folder_only=True)
		if not drive_category_type_folders:
			logger.error("No category type folders found in root folder.")
			task_service.close()
			return False

		deleted_category_types = 0
		deleted_categories = 0
		deleted_shortcuts = 0

		for drive_category_type_folder in drive_category_type_folders:
			# Cleaning category type folders that are not in db
			if drive_category_type_folder.drive_file_id not in [f.drive_file_id for f in all_files]:
				logger.debug(
					f"Removing category_type folder {drive_category_type_folder.name} with ID {drive_category_type_folder.drive_file_id} from drive.")
				try:
					self.api_client.remove_drive_file(task_service, drive_category_type_folder.drive_file_id)
					deleted_category_types += 1
				except Exception as e:
					logger.error(f"Failed to remove folder {drive_category_type_folder.name}: {e}")
				continue

			# Cleaning category folders that are not in db
			drive_category_folders = self.get_folder_files(drive_category_type_folder.drive_file_id)
			for drive_category_folder in drive_category_folders:
				if drive_category_folder.drive_file_id not in [f.drive_file_id for f in all_files]:
					logger.debug(
						f"Removing category folder {drive_category_folder.name} with ID {drive_category_folder.drive_file_id} from drive.")
					try:
						self.api_client.remove_drive_file(task_service, drive_category_folder.drive_file_id)
						deleted_categories += 1
					except Exception as e:
						logger.error(f"Failed to remove folder {drive_category_folder.name}: {e}")
					continue

				if drive_category_folder.mime_type != "application/vnd.google-apps.folder":
					continue

				# Cleaning shortcuts that are not in db
				drive_shortcuts = self.get_folder_files(drive_category_folder.drive_file_id)
				for shortcut in drive_shortcuts:
					if shortcut.drive_file_id not in [f.drive_file_id for f in all_files]:
						logger.debug(f"Removing shortcut {shortcut.name} with ID {shortcut.drive_file_id} from drive.")
						try:
							self.api_client.remove_drive_file(task_service, shortcut.drive_file_id)
							deleted_shortcuts += 1
						except Exception as e:
							logger.error(f"Failed to remove shortcut {shortcut.name}: {e}")


		task_service.close()
		logger.info("Deleted obsolete entries from Drive: "
					f"{deleted_category_types} category type folders, "
					f"{deleted_categories} category folders, "
					f"{deleted_shortcuts} shortcuts.")
		return True
