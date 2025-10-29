from src.db.query_options import FileQueryOptions
from src.models.file import File
from src.models.category import Category
from src.models.category_type import CategoryType
from src.models.category_alias import CategoryAlias
from main import logger


class CategoryService:
	@staticmethod
	def generate_potential_aliases(parent_drive_file_ids: list[str] = None):
		"""
		Generates a list of unique folder names that are direct children
		of the given parent folders. If parent_drive_file_ids is None, scans top-level folders.

		:param parent_drive_file_ids: List of drive_file_id of parent folders to scan.
									  If None, it looks for folders without parents (top-level).
		:return: List of strings containing folder names.
		"""
		if parent_drive_file_ids is None:
			out_folders = File.get_root_folders()
		elif not parent_drive_file_ids:
			logger.info("No parent folders to scan. No aliases generated.")
			return []
		else:
			folders = File.get_files_by_ids(parent_drive_file_ids, FileQueryOptions(folder_only=True))
			out_folders = File.get_files_from_folders(folders, FileQueryOptions(folder_only=True))

		return sorted(list(set([f.name for f in out_folders])))

	@staticmethod
	def delete_category_type(category_type: CategoryType):
		"""
		Deletes all categories associated with a given category type,
		as well as the category type itself.

		:param category_type: CategoryType object to delete.
		"""
		if category_type.delete():
			logger.info(f"Deleted category type '{category_type.name}' along with its associated categories.")

	@staticmethod
	def load_aliases(config_data: list[dict], category_type: CategoryType):
		"""
		Loads alias configuration and adds them to the database,
		then consolidates associated files/folders.

		:param config_data: Dictionary with alias configuration data (usually loaded from JSON).
		:param category_type: CategoryType object, e.g., CategoryType("Virtual Folder").
		"""

		for category_obj in config_data:
			canonical_name = category_obj.get("canonical_name")
			aliases = category_obj.get("aliases")

			if not canonical_name:
				logger.warning(f"Found a category object without 'canonical_name'. Skipping: {category_obj}")
				continue
			if aliases is None:
				logger.warning(f"Found a category object without 'aliases'. Skipping: {category_obj}")
				return

			if not isinstance(aliases, list):
				logger.warning(f"Aliases for '{canonical_name}' is not a list. Skipping aliases: {aliases}")
				return

			category = Category.find_or_create(category_type.id, canonical_name)
			if not category:
				logger.error(f"Failed to create or retrieve canonical category '{canonical_name}'.")
				continue

			for alias_name in aliases:
				if alias_name and isinstance(alias_name, str):
					CategoryAlias.find_or_create(category.id, alias_name)
					logger.debug(f"Added alias: '{alias_name}' for category '{canonical_name}'")
				else:
					logger.warning(f"Invalid alias found for '{canonical_name}': '{alias_name}'. Skipping.")
