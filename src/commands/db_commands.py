import src.utils as utils
from src.db.database import setup_database
from src.models.file import File
from main import logger, db_checker
from src.db.db_integrity_checker import IntegrityLevel


def initialize_database(args):
	"""Initializes the database (creates tables)."""
	setup_database()
	logger.info("Database initialized successfully.")


def update_data_in_database(args):
	"""Updates the database with new data from a JSON file."""
	file_with_data = args.file_with_data

	if not db_checker.test_db_integrity(IntegrityLevel.BASE):
		return

	if not file_with_data:
		logger.error("file_with_data is required for updating data.")
		return
	from src.services.update_service import UpdateService

	UpdateService.data_update(file_with_data)


def set_root_folder_id(args) -> bool:
	"""Sets the root folder"""
	root_folder_id = args.root_folder_id
	root_folder_force = args.force or False
	if not root_folder_id:
		logger.error("root_folder_id is required.")
		return False

	if not db_checker.test_db_integrity(IntegrityLevel.STRUCTURE):
		return False

	from src.models.drive_file import DriveFile
	from src.models.category_type import CategoryType
	current_root_folder_id = DriveFile.get_drive_files_by_level(0)[
		0].drive_file_id if DriveFile.get_drive_files_by_level(0) else None

	if current_root_folder_id and not root_folder_force:
		logger.erorr(
			f"Root folder already exists with ID: {current_root_folder_id}. Use --force to reset. It will delete all existing entries.")
		return False

	# If there are any files in the database, delete all categories
	# if db_checker.test_db_integrity(db_checker.IntegrityLevel.FILES):

	# I hope this won't backfire
	#     CategoryType.delete_all()
	DriveFile.delete_all()

	from src.drive.drive_scanner import DriveScanner
	drive_scanner = DriveScanner()
	root_folder = drive_scanner.get_file(root_folder_id)
	if not root_folder:
		logger.error(f"Could not find folder with ID: {root_folder_id}")
		return False
	DriveFile.add_drive_file(root_folder, 0)

	logger.info(f"Root folder ID set to: {root_folder_id}")
	return True


def create_root_folder(args):
	"""Creates a root folder in Google Drive."""
	from src.drive.drive_builder import DriveBuilder
	from src.models.drive_file import DriveFile

	root_folder_name = args.root_folder_name
	root_folder_location = args.root_folder_location or ""
	root_folder_force = args.force or False

	if not db_checker.test_db_integrity(IntegrityLevel.STRUCTURE):
		return False

	drive_builder = DriveBuilder()
	if drive_builder.root_folder_id and not root_folder_force:
		logger.error(
			f"Root folder already exists with ID: {drive_builder.root_folder_id}. Use --force to recreate. It will delete all existing entries.")
		return

	# from src.models.category_type import CategoryType
	# CategoryType.delete_all()
	DriveFile.delete_all()

	root_folder_id = drive_builder.create_root_folder(root_folder_name, root_folder_location)
	if root_folder_id:
		logger.info(f"Root folder created successfully with ID: {root_folder_id}")
	else:
		logger.error("Root folder creation failed.")


def add_db_parsers(subparsers):
	"""Adds database-related subparsers to the main parser."""

	# Command: init-db
	init_parser = subparsers.add_parser("init-db", help="Initializes the database.")
	init_parser.set_defaults(func=initialize_database)

	# Command: update-data
	update_parser = subparsers.add_parser("update-data", help="Updates the database with new data from a JSON file.")
	update_parser.add_argument("file_with_data", type=str,
							   help="JSON file containing new data to update the database.")
	update_parser.set_defaults(func=update_data_in_database)

	# Command: set-root-folder
	set_root_parser = subparsers.add_parser("set-root-folder", help="Sets the root folder ID in the database.")
	set_root_parser.add_argument("root_folder_id", type=str, help="The ID of the root folder.")
	set_root_parser.add_argument("--force", action="store_true",
								 help="Force reset the root folder ID, deleting all existing entries.")
	set_root_parser.set_defaults(func=set_root_folder_id)
	# Command: create-root-folder

	create_root_parser = subparsers.add_parser("create-root-folder",
											   help="Creates a root folder in Google Drive and sets it in the database.")
	create_root_parser.add_argument("root_folder_name", type=str, help="The name of the root folder to create.")
	create_root_parser.add_argument("--root_folder_location", type=str, default="",
									help="The location (parent folder ID) to create the root folder in Google Drive.")
	create_root_parser.add_argument("--force", action="store_true",
									help="Force recreate the root folder, deleting all existing entries.")
	create_root_parser.set_defaults(func=create_root_folder)
