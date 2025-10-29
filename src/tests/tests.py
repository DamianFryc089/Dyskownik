# test_example.py
import unittest
from time import sleep

from main import config_data
from src import utils
from src.commands.category_commands import load_category_type
from src.commands.db_commands import set_root_folder_id
from src.commands.drive_commands import drive_update
from src.db.database import drop_database
from src.db.query_options import FileQueryOptions
from src.drive.drive_scanner import DriveScanner
from src.models.category_type import CategoryType
from src.models.drive_file import DriveFile

import os

SKIP_HEAVY_TESTS = config_data.skip_heavy_tests


class Tester(unittest.TestCase):
	def setUp(self):
		self.files_data_path_test = 'test_data/files_t.json'
		self.starting_folders_path = 'test_data/starting_folders.txt'

		self.files_data_path = 'test_data/files.json'
		self.db_path_test = 'test_data/data_t.db'
		self.db_path = 'test_data/data_for_drive.db'

		self.aliases_from_starting_folders_path_test = 'test_data/aliases_from_starting_folders_t.json'
		self.aliases_from_starting_folders_path = 'test_data/aliases_from_starting_folders.json'

	@unittest.skipIf(SKIP_HEAVY_TESTS, "Skipping scan test to avoid heavy operations.")
	def test_scan(self):
		from src.commands.drive_commands import drive_fetch_data

		no_file = drive_fetch_data(type('Args', (object,), {
			'start_folders_file': 'test_data/non_existing_file.txt',
			'json_file': self.files_data_path_test,
			'max_workers': 25,
			'save_every_files': 10000000,
			'search_parent': True
		})())
		self.assertFalse(no_file)

		normal = drive_fetch_data(type('Args', (object,), {
			'start_folders_file': self.starting_folders_path,
			'json_file': self.files_data_path_test,
			'max_workers': 100,
			'save_every_files': 10000000,
			'search_parent': True
		})())
		self.assertTrue(normal)

		files_data = utils.get_json(self.files_data_path_test)
		self.assertIsNotNone(files_data)
		self.assertIsInstance(files_data, list)
		self.assertEqual(len(files_data), 41)

	def test_db_start(self):
		config_data.database_file = self.db_path_test
		from src.commands.db_commands import initialize_database, update_data_in_database
		drop_database()
		initialize_database(None)
		update_data_in_database(type('Args', (object,), {'file_with_data': self.files_data_path})())

		from src.models.file import File
		files = File.get_all(options=FileQueryOptions(exclude_shortcuts=False))
		self.assertIsInstance(files, list)
		self.assertEqual(len(files), 41)

		from src.commands.category_commands import generate_aliases_from_folders
		generate_aliases_from_folders(type('Args', (object,), {
			'input_file': self.starting_folders_path,
			'output_file': self.aliases_from_starting_folders_path_test
		})())

		generated_aliases = utils.get_json(self.aliases_from_starting_folders_path_test)
		expected_aliases = utils.get_json(self.aliases_from_starting_folders_path)

		self.assertIsNotNone(generated_aliases)
		unassigned_folders: list[str] = generated_aliases.get("unassigned_folders", [])
		categories = expected_aliases.get("categories", [])
		all_aliases: list[str] = [alias for cat in categories for alias in cat.get("aliases", [])]

		self.assertEqual(sorted(unassigned_folders), sorted(all_aliases))

		load_category_type(type('Args', (object,), {
			'input_file': self.aliases_from_starting_folders_path
		})())

		from src.models.category_type import CategoryType
		from src.models.category import Category
		from src.models.category_alias import CategoryAlias

		category_type = CategoryType.get_by_name("Category_A")
		self.assertIsNotNone(category_type)

		categories = Category.get_by_type(category_type)
		self.assertEqual(len(categories), 3)

		categories_aliases = []
		for category in categories:
			aliases = CategoryAlias.get_by_category(category)
			categories_aliases.extend(aliases)
		self.assertEqual(len(categories_aliases), 5)

	@unittest.skipIf(SKIP_HEAVY_TESTS, "Skipping building test to avoid heavy operations.")
	def test_build_drive(self):
		config_data.database_file = self.db_path
		DriveFile.delete_all()
		no_root_test = drive_update(None)
		self.assertFalse(no_root_test)

		if not config_data.test_drive_folder_id:
			self.skipTest("TEST_DRIVE_FOLDER_ID not set in environment variables.")

		set_root = set_root_folder_id(type('Args', (object,), {
			'root_folder_id': config_data.test_drive_folder_id,
			'force': False
		})())
		load_category_type(type('Args', (object,), {
			'input_file': self.aliases_from_starting_folders_path
		})())
		self.assertIsNotNone(set_root)
		root_folder = DriveFile.get_drive_files_by_level(0)
		self.assertIsNotNone(root_folder)

		# Build drive structure
		test_update = drive_update(None)
		self.assertTrue(test_update)

		# Check if files were created
		cat_folder = DriveFile.get_drive_files_by_level(1, CategoryType.get_by_name("Category_A"))[0]
		self.assertIsNotNone(cat_folder)

		scanner = DriveScanner()
		file_info = scanner.get_file(cat_folder.drive_file_id)
		self.assertIsNotNone(file_info)

		# Delete the file from database and update drive again
		CategoryType.delete_all()
		test_delete = drive_update(None)
		self.assertTrue(test_delete)

		# Check if the file is gone
		file_info = scanner.get_file(cat_folder.drive_file_id)
		self.assertIsNone(file_info)
		DriveFile.delete_all()



if __name__ == "__main__":
	unittest.main()

