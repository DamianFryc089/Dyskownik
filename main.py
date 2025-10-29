import argparse
import os
from dotenv import load_dotenv

from src.config_data import ConfigData
from src.logger import Logger

load_dotenv()
config_data = ConfigData(os.environ)

logger = Logger.get_logger(__name__, level=config_data.logger_level, log_file=config_data.log_file)

from src.db.db_integrity_checker import DBIntegrityChecker

db_checker = DBIntegrityChecker()

from src.commands import db_commands
from src.commands import drive_commands
from src.commands import category_commands


def main():
	parser = argparse.ArgumentParser(description="Tool for indexing and managing Google Drive files.")
	subparsers = parser.add_subparsers(dest="command", help="Available commands")

	db_commands.add_db_parsers(subparsers)
	drive_commands.add_drive_parsers(subparsers)
	category_commands.add_categories_parsers(subparsers)

	# Parse arguments
	args = parser.parse_args()

	# Call the appropriate function based on the command
	if hasattr(args, 'func'):
		# Pass the entire args object to the function
		args.func(args)
	else:
		parser.print_help()  # Display help if no command is provided


if __name__ == '__main__':
	main()
