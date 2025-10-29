from main import logger
from src.db.database import get_db_connection
from src.db.query_options import FileQueryOptions
from src.models.base_model import BaseModel


class CategoryType(BaseModel):
	_table_name = 'category_types'

	def __init__(self, id=None, name=None, aggregation_type=None):
		super().__init__(id=id, name=name)
		self.id = id
		self.name = name
		self.aggregation_type = aggregation_type

	@classmethod
	def get_all(cls):
		"""Returns all category types."""
		query = f"SELECT ct.* FROM {cls._table_name} ct"
		rows = cls._execute_query(query)
		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_by_name(cls, name):
		"""
		Fetches a category type by name.

		:param name: Name of the category type.
		:return: CategoryType object or None if not found.
		"""
		query = f"SELECT * FROM {cls._table_name} WHERE name = ?"
		row = cls._execute_query(query, (name,), fetch_one=True)
		return cls(**dict(row)) if row else None

	@classmethod
	def delete_all(cls):
		query = f"DELETE FROM {cls._table_name}"
		outcome = cls._execute_query(query)
		if outcome is not None:
			from src.models.drive_file import DriveFile
			DriveFile.delete_all(skip_root=True)
			return True
		else:
			return False

	def delete(self):
		"""Deletes the category type and all associated categories."""
		query = f"DELETE FROM {self._table_name} WHERE id = ?"
		outcome = self._execute_query(query, (self.id,))
		if outcome is not None:
			from src.models.drive_file import DriveFile
			DriveFile.delete_by_category_type(self)
			return True
		else:
			return False

	@classmethod
	def find_or_create(cls, name, aggregation_type=None, ):
		"""Fetches a category type by name or creates a new one."""
		conn = get_db_connection()
		c = conn.cursor()
		try:
			c.execute(f"SELECT ct.*  FROM {cls._table_name} ct WHERE ct.name = ?", (name,))
			row = c.fetchone()
			if row:
				return cls(**dict(row))
			elif aggregation_type is not None:
				aggregation_type = aggregation_type.lower()
				if aggregation_type not in ['shortcut', 'collection', 'pattern']:
					logger.error(
						f"Unknown aggregation type '{aggregation_type}' provided for category type '{name}'. Valid types are 'shortcut', 'collection', 'pattern'.")

					return None
				c.execute(f"INSERT INTO {cls._table_name} (name, aggregation_type) VALUES (?, ?)",
						  (name, aggregation_type))
				conn.commit()
				return cls(id=c.lastrowid, name=name, aggregation_type=aggregation_type)
			else:
				logger.error(
					f"Category type '{name}' does not exist and no aggregation type provided. Cannot create.")
				return None
		finally:
			conn.close()

	def link_all_files(self, temp=False):
		from src.models.category import Category
		from src.models.file import File
		from src.models.category_alias import CategoryAlias

		categories = Category.get_by_type(self)
		for category in categories:
			category_aliases = CategoryAlias.get_by_category(category)
			if not category_aliases:
				logger.warning(f"Category '{category.canonical_name}' has no aliases. Skipping consolidation.")
				continue

			files = []
			match self.aggregation_type:
				case 'shortcut':
					files = File.get_files_by_names([alias.alias_name for alias in category_aliases],
													FileQueryOptions(temp=temp))
					if files.__len__() > 1:
						info = [f"'{file.name}' (ID: {file.id})" for file in files]
						logger.warning(
							f"Category '{category.canonical_name}' has multiple files linked to aliases: {', '.join(info)}. Consolidating to one file.")
						files = [files[0]]
				case 'collection':
					folders = File.get_files_by_names([alias.alias_name for alias in category_aliases],
													  FileQueryOptions(folder_only=True, temp=temp))
					files = File.get_files_from_folders(folders, FileQueryOptions(temp=temp))
				case 'pattern':
					files = File.get_files_by_regex([alias.alias_name for alias in category_aliases],
													FileQueryOptions(temp=temp))
				case _:
					logger.error(
						f"Unknown aggregation type '{self.aggregation_type}' for category '{category.canonical_name}'. Skipping consolidation.")
					return

			if not files:
				logger.info(
					f"No files found for category '{category.canonical_name}' with aggregation type '{self.aggregation_type}'.")
				continue

			for file in files:
				category.link_file(file.id, temp)
				logger.info(
					f"Linked file '{file.name}' (ID: {file.id}) to canonical category '{category.canonical_name}'.")

	def __repr__(self):
		return f"<CategoryType(id={self.id}, name='{self.name}')>"
