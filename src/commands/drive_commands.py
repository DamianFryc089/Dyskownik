from src.db.db_integrity_checker import IntegrityLevel
from src.drive import drive_scanner
from src.drive.drive_builder import DriveBuilder
from src.models.category_type import CategoryType
from src.services.update_service import UpdateService
from main import logger, db_checker, config_data


def drive_fetch_data(args) -> bool:
	"""
	Fetches data from Google Drive and saves it in JSON.

	:param args: An argparse.Namespace object containing parsed command-line arguments.
				 Expected attributes: start_folders_file, json_file, max_workers, save_every_files, search_parent.
	"""
	start_folders_file = args.start_folders_file
	json_file = args.json_file
	max_workers = args.max_workers
	save_every_files = args.save_every_files
	search_parent = args.search_parent

	logger.info("Initiating Google Drive data fetching process.")
	logger.info(
		f"Parameters - start_folders_file: {start_folders_file}, json_file: {json_file}, max_workers: {max_workers}, save_every_files: {save_every_files}, search_parent: {search_parent}")

	result = drive_scanner.run_normal(
		starting_folders_file=start_folders_file,
		json_file=json_file,
		max_workers=max_workers,
		save_every_files=save_every_files,
		search_parent=search_parent
	)
	if not result:
		logger.error("Google Drive data fetching process failed.")
		return False

	logger.info("Google Drive data fetching process completed successfully.")
	return True


def drive_update(args) -> bool:
	"""
	Updates Google Drive structure based on current database state.
	"""
	try:
		if not db_checker.test_db_integrity(IntegrityLevel.ROOT_ONLY):
			return False
		UpdateService.drive_update_all()
	except Exception as e:
		logger.error(f"An unhandled error occurred during Google Drive update: {e}")
		return False
	logger.info("Google Drive update completed successfully.")
	return True


def start_server(args) -> bool:
	"""Starts a server that periodically fetches data from Google Drive and updates the database."""
	main_folders_file = args.main_folders_file or config_data.server_main_folders_file or "auto_main_folders.txt"
	scan_file = args.scan_file or config_data.server_scan_file or "auto_scan.json"
	scan_interval = args.scan_interval or config_data.server_scan_interval or 60 * 60 * 24
	max_workers = args.max_workers or config_data.server_max_workers or 10
	save_every_files = args.save_every_files or config_data.server_save_every_files or 10000000
	search_parent = args.search_parent or config_data.server_search_parent or False

	if not db_checker.test_db_integrity(IntegrityLevel.FULL):
		return False

	from src.services.server_service import ServerService
	server_service = ServerService()
	server_service.main_folders_file = main_folders_file
	server_service.scan_file = scan_file
	server_service.max_workers = max_workers
	server_service.save_every_files = save_every_files
	server_service.search_parent = search_parent

	server_service.start_server(scan_interval)
	return True


def add_drive_parsers(subparsers):
	"""Adds Google Drive-related subparsers to the main parser."""

	# Command: drive-fetch
	fetch_parser = subparsers.add_parser(
		"drive-fetch",
		help="Fetches data from Google Drive and saves it in a JSON file."
	)
	fetch_parser.add_argument(
		"start_folders_file",
		type=str,
		help="Text file containing IDs of root folders to start fetching from."
	)
	fetch_parser.add_argument(
		"--json-file",
		type=str,
		default="files.json",  # Provide a sensible default
		help="Name of the JSON file to save the fetched data (default: files.json)."
	)
	fetch_parser.add_argument(
		"--max-workers",
		type=int,
		default=5,  # Default to 5 workers for concurrent fetching
		help="Maximum number of worker threads for concurrent fetching."
	)
	fetch_parser.add_argument(
		"--save-every-files",
		type=int,
		default=500,  # A reasonable default for saving progress
		help="Number of files to process before saving collected data to JSON (default: 500)."
	)
	fetch_parser.add_argument(
		"--search-parent",
		action="store_true",  # True if the user wants to search for parent folders
		help="Enable searching for parent folder during the scan (default: False)."
	)
	fetch_parser.set_defaults(func=drive_fetch_data)

	# Command: drive-update
	update_parser = subparsers.add_parser(
		"drive-update",
		help="Updates Google Drive structure based on current database state."
	)
	update_parser.set_defaults(func=drive_update)

	# Command: start-server
	server_parser = subparsers.add_parser(
		"start-server",
		help="Starts a server that periodically fetches data from Google Drive, updates the database and updates the Drive structure accordingly."
	)
	server_parser.add_argument(
		"--main-folders-file",
		type=str,
		help="Text file containing IDs of main folders to monitor (default: auto_main_folders.txt)."
	)
	server_parser.add_argument(
		"--scan-file",
		type=str,
		help="JSON file to save the fetched scan data (default: auto_scan.json)."
	)
	server_parser.add_argument(
		"--scan-interval",
		type=int,
		help="Interval in seconds between scans (default: 24 hours)."
	)
	server_parser.add_argument(
		"--max-workers",
		type=int,
		help="Maximum number of worker threads for concurrent fetching (default: 10)."
	)
	server_parser.add_argument(
		"--save-every-files",
		type=int,
		help="Number of files to process before saving collected data to JSON (default: 10000000)."
	)
	server_parser.add_argument(
		"--search-parent",
		action="store_true",
		help="Enable searching for parent folder during the scan (default: False)."
	)
	server_parser.set_defaults(func=start_server)
