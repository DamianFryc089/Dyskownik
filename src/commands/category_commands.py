import src.utils as utils
from src.db.query_options import FileQueryOptions
from src.models.category import Category
from src.models.category_type import CategoryType
from src.models.file import File
from src.services.category_service import CategoryService
from main import db_checker
from src.db.db_integrity_checker import IntegrityLevel
from main import logger


def generate_aliases_from_folders(args):
	"""
	Generates aliases based on folder IDs provided in the input file.
	Aliases are created from the unique names of the parent folders
	of the specified folders.
	"""
	input_file = args.input_file
	output_file = args.output_file

	logger.info(f"Generating aliases from file: {input_file}")

	folder_ids = utils.get_lines_from_file(input_file, True)
	if folder_ids:
		aliases_names = CategoryService.generate_potential_aliases(folder_ids)
		utils.save_aliases_to_json(aliases_names, output_file)
		logger.info(f"Aliases generated and saved to {output_file}")
	else:
		logger.error(f"No main folders in {input_file} to generate aliases from.")


def generate_aliases_for_category_type(args):
	"""
	Generates aliases from unique folder names associated with a specified category type.

	This function identifies folders linked to the given `category_type_name`
	(e.g., 'Subjects', 'Semesters'). It then extracts unique folder names
	(or their parent folder names, depending on how `generate_potential_aliases` works)
	to serve as potential aliases.

	If an `extra_aliases_file` is provided, the function also reads folder names
	from that file, finds their corresponding IDs, and includes them in the alias generation process.
	The final set of aliases is saved to the specified `output_file` in JSON format.
	"""
	category_type_name = args.category_type_name
	output_file = args.output_file
	extra_aliases_file = args.extra_aliases

	logger.info(f"Generating aliases for category type '{category_type_name}' based on existing folders...")
	category_type = CategoryType.find_or_create(category_type_name)
	if not category_type:
		logger.error(f"Category type '{category_type.name}' not found.")
		return

	folders = File.get_files_from_category_type(category_type, FileQueryOptions(folder_only=True))
	folder_ids = [f.drive_file_id for f in folders]

	if extra_aliases_file:
		extra_aliases = utils.get_lines_from_file(extra_aliases_file)
		extra_folders = File.get_files_by_names(extra_aliases, FileQueryOptions(folder_only=True))
		folder_ids.extend([f.drive_file_id for f in extra_folders])

	if folder_ids:
		aliases_names = CategoryService.generate_potential_aliases(list(set(folder_ids)))
		utils.save_aliases_to_json(aliases_names, output_file)
		logger.info(f"Aliases generated and saved to {output_file}")
	else:
		logger.error(f"No folders found for category type '{category_type_name}' to generate aliases from.")


def load_category_type(args):
	"""Loads aliases from a JSON file into the database."""
	input_file = args.input_file

	if not db_checker.test_db_integrity(IntegrityLevel.STRUCTURE):
		return False

	categories_data = utils.get_json(input_file)
	if categories_data is None or not isinstance(categories_data, dict):
		logger.error(f"Could not load data from {input_file}. Please check the file format.")
		return

	if "category_type_name" not in categories_data:
		logger.error(f"Error: The file {input_file} does not contain 'category_type_name' key.")
		return
	if "aggregation_type" not in categories_data:
		logger.error(f"Error: The file {input_file} does not contain 'aggregation_type' key.")
		return
	if "categories" not in categories_data:
		logger.error(f"Error: The file {input_file} does not contain 'categories' key.")
		return

	logger.info(
		f"Loading aliases from '{input_file}' for category type '{categories_data.get('category_type_name')}'...")

	category_type = CategoryType.find_or_create(categories_data.get("category_type_name"),
												categories_data.get("aggregation_type"))
	if not category_type:
		logger.error(f"Could not create/retrieve category type '{categories_data.get('category_type_name')}'.")
		return

	Category.get_by_type(category_type)
	for cat in Category.get_by_type(category_type):
		cat.delete()
	CategoryService.load_aliases(categories_data.get("categories"), category_type)
	logger.info(f"Linking files to categories for category type '{categories_data.get('category_type_name')}'...")
	category_type.link_all_files(temp=False)
	logger.info(
		f"Aliases from '{input_file}' for category type '{categories_data.get('category_type_name')}' loaded successfully.")


def remove_category_type(args):
	"""Removes a category type from the database by its name."""
	category_type_name = args.category_type_name
	logger.info(f"Removing category type with name: {category_type_name}")

	if not db_checker.test_db_integrity(IntegrityLevel.STRUCTURE):
		return False

	category = CategoryType.get_by_name(category_type_name)
	if not category:
		logger.error(f"Category type with name {category_type_name} not found.")
		return

	category.delete()
	logger.info(f"Category type with name {category_type_name} removed successfully.")


def add_categories_parsers(subparsers):
	"""Adds category-related subparsers to the main parser."""

	# Command: gen-aliases-for-file
	gen_file_aliases_parser = subparsers.add_parser("gen-aliases-for-file",
													help="Generates aliases based on folder IDs provided in an input file. Aliases are derived from the unique names of the parent folders of the specified IDs.")
	gen_file_aliases_parser.add_argument("input_file", type=str, help="File containing folder IDs.")
	gen_file_aliases_parser.add_argument("--output_file", type=str, default="category_aliases.json",
										 help="File to save generated aliases in JSON format.")
	gen_file_aliases_parser.set_defaults(func=generate_aliases_from_folders)

	# Command: gen-aliases-for-category
	gen_cat_aliases_parser = subparsers.add_parser("gen-aliases-for-category-type",
												   help="Generates aliases from unique folder names or file names associated with a specific category type.")
	gen_cat_aliases_parser.add_argument("category_type_name", type=str,
										help="The name of the category type to generate aliases for.")
	gen_cat_aliases_parser.add_argument("--output_file", type=str, default="category_aliases.json",
										help="File to save generated aliases in JSON format.")
	gen_cat_aliases_parser.add_argument("--extra-aliases", type=str, default=None,
										help="Path to a file containing additional folder names to include in the generation process.")
	gen_cat_aliases_parser.set_defaults(func=generate_aliases_for_category_type)

	# Command: load-aliases
	load_aliases_parser = subparsers.add_parser("load-category-type",
												help="Creates a category type and loads categories with their aliases from a JSON file into the database. Also used to update existing category types.")
	load_aliases_parser.add_argument("input_file", type=str, help="JSON file with category name and alias definitions.")
	load_aliases_parser.set_defaults(func=load_category_type)

	# Command: delete-category-type
	delete_category_parser = subparsers.add_parser("delete-category-type",
												   help="Deletes a category type from the database by its name.")
	delete_category_parser.add_argument("category_type_name", type=str, help="Name of the category type to delete.")
	delete_category_parser.set_defaults(func=remove_category_type)
