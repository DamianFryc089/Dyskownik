from src.db.db_integrity_checker import IntegrityLevel
from src.drive import drive_scanner
from src.drive.drive_builder import DriveBuilder
from src.models.category_type import CategoryType
from src.services.update_service import UpdateService
from main import logger, db_checker


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
	main_folders_file = args.main_folders_file or "auto_main_folders.txt"
	scan_file = args.scan_file or "auto_scan.json"
	scan_interval = args.scan_interval or 60 * 60 * 24

	if not db_checker.test_db_integrity(IntegrityLevel.FULL):
		return False

	from src.services.server_service import ServerService
	server_service = ServerService(main_folders_file, scan_file)
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
		default="auto_main_folders.txt",
		help="Text file containing IDs of main folders to monitor (default: auto_main_folders.txt)."
	)
	server_parser.add_argument(
		"--scan-file",
		type=str,
		default="auto_scan.json",
		help="JSON file to save the fetched scan data (default: auto_scan.json)."
	)
	server_parser.add_argument(
		"--scan-interval",
		type=int,
		default=60 * 60 * 24,  # Default to 24 hours
		help="Interval in seconds between scans (default: 24 hours)."
	)
	server_parser.set_defaults(func=start_server)
