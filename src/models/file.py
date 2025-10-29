from main import logger
from src.db.query_options import FileQueryOptions
from src.models.base_model import BaseModel
from src.db.database import get_db_connection
from src.models.category import Category
from src.models.category_type import CategoryType


class File(BaseModel):
	_table_name = 'files'

	def __init__(self, id=None, drive_file_id=None, name=None, mime_type=None,
				 parent_id=None, owner=None, created_time=None, modified_time=None,
				 size=None, shortcut_target_id=None, md5_checksum=None, active=None):
		super().__init__(
			id=id, drive_file_id=drive_file_id, name=name, mime_type=mime_type,
			parent_id=parent_id, owner=owner, created_time=created_time,
			modified_time=modified_time, size=size, shortcut_target_id=shortcut_target_id,
			md5_checksum=md5_checksum, active=active
		)
		self.id = id
		self.drive_file_id = drive_file_id
		self.name = name
		self.mime_type = mime_type
		self.parent_id = parent_id
		self.owner = owner
		self.created_time = created_time
		self.modified_time = modified_time
		self.size = size
		self.shortcut_target_id = shortcut_target_id
		self.md5_checksum = md5_checksum
		self.active = active

	@classmethod
	def from_api_response(cls, file: dict) -> 'File':

		parents = file.get("parents", [])
		parent_id = parents[0] if parents else None

		owners = file.get("owners", [])
		owner = owners[0]['emailAddress'] if owners else None

		shortcut_details = file.get("shortcutDetails", {})
		shortcut_target_id = shortcut_details.get("targetId") if shortcut_details else None

		remapped_data = {
			"drive_file_id": file.get("id"),
			"name": file.get("name"),
			"mime_type": file.get("mimeType"),
			"parent_id": parent_id,
			"owner": owner,
			"created_time": file.get("createdTime"),
			"modified_time": file.get("modifiedTime"),
			"size": file.get("size"),
			"shortcut_target_id": shortcut_target_id,
			"md5_checksum": file.get("md5Checksum"),
			"active": 1
		}

		return cls(**remapped_data)

	@classmethod
	def add_batch(cls, files_data: list[dict], options: FileQueryOptions = None) -> int | None:
		"""
		Adds multiple files to the database using a transaction.
		Data is inserted into the specified table (default: cls._table_name).

		:param options: Filter options for file queries.
		:param files_data: List of dictionaries, each representing file data.
		"""
		conn = get_db_connection()
		try:
			with conn:
				options = options if options else FileQueryOptions()
				c = conn.cursor()

				columns = [
					'drive_file_id', 'name', 'mime_type', 'parent_id',
					'owner', 'created_time', 'modified_time', 'size',
					'shortcut_target_id', 'md5_checksum'
				]
				placeholders = ', '.join(['?' for _ in columns])

				query = f"INSERT OR IGNORE INTO {options.table_name.split(' ')[0]} ({', '.join(columns)}) VALUES ({placeholders})"

				data_tuples = []
				for file_data in files_data:
					data_tuples.append((
						file_data['drive_file_id'],
						file_data['name'],
						file_data['mime_type'],
						file_data.get('parent_id'),
						file_data.get('owner'),
						file_data.get('created_time'),
						file_data.get('modified_time'),
						file_data.get('size'),
						file_data.get('shortcut_target_id'),
						file_data.get('md5_checksum')
					))

				c.executemany(query, data_tuples)
				return c.rowcount
		except Exception as e:
			logger.error(f"Unexpected error while adding batch files to {options.table_name}: {e}")
			return None

	@classmethod
	def replace_files(cls):
		"""
		Deletes all existing files from the main 'files' table
		and replaces them with files from the temporary 'files_temp' table.
		This operation is executed in a single transaction.
		"""
		conn = get_db_connection()
		try:
			with conn:
				conn.execute(f"DELETE FROM {cls._table_name};")

				conn.execute(f"""
                    INSERT INTO {cls._table_name}
                    (id, drive_file_id, name, mime_type, parent_id, owner, created_time, modified_time, size, shortcut_target_id, md5_checksum, active)
                    SELECT id, drive_file_id, name, mime_type, parent_id, owner, created_time, modified_time, size, shortcut_target_id, md5_checksum, active
                    FROM files_temp;
                """)

				conn.execute("DELETE FROM files_temp;")
		except Exception as e:
			logger.error(f"Unexpected error occurred while replacing files: {e}")
			raise

	@classmethod
	def deactivate_files(cls, files: list['File']) -> int | None:
		"""
		Deactivates the given files in the database by setting their 'active' flag to 0.
		Files are identified by their database 'id'.

		:param files: List of File objects to deactivate.
		"""
		if not files:
			logger.info("No files provided for deactivation.")
			return None

		conn = get_db_connection()
		try:
			with conn:
				cursor = conn.cursor()
				file_ids_to_deactivate = [(f.id,) for f in files if f.id is not None]

				if not file_ids_to_deactivate:
					logger.info("No valid file IDs found for deactivation.")
					return

				query = f"UPDATE {cls._table_name} SET active = 0 WHERE id = ?"

				cursor.executemany(query, file_ids_to_deactivate)
				return cursor.rowcount
		except Exception as e:
			logger.error(f"Unexpected error during file deactivation: {e}")
			return None

	@classmethod
	def get_files_by_regex(cls, regex_patterns: list[str], options: FileQueryOptions = None) -> list['File']:
		"""
		Retrieves files/folders whose names match a list of regular expressions.

		:param options:
		:param regex_patterns: List of regex strings.
		:return: List of File objects whose names match the provided regexes.
		"""
		if not regex_patterns:
			return []

		options = options if options else FileQueryOptions()
		regex_conditions = ["name REGEXP ?" for _ in regex_patterns]
		conditions_str = " OR ".join(regex_conditions)

		query = f"SELECT * FROM {options.table_name} WHERE ({conditions_str}) {options.get_full_filter_sql()}"

		rows = cls._execute_query(query, tuple(regex_patterns))

		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_files_by_names(cls, folder_names: list[str], options: FileQueryOptions = None) -> list['File']:
		"""Retrieves folders based on their names."""
		if not folder_names:
			return []
		options = options if options else FileQueryOptions()
		placeholders = ','.join('?' for _ in folder_names)

		query = f"SELECT * FROM {options.table_name} WHERE name IN ({placeholders}) {options.get_full_filter_sql()}"
		rows = cls._execute_query(query, folder_names)
		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_files_by_ids(cls, files_ids: list[str], options: FileQueryOptions = None) -> list['File']:
		"""Retrieves files based on their IDs."""
		if not files_ids:
			return []
		options = options if options else FileQueryOptions()
		placeholders = ','.join('?' for _ in files_ids)
		query = f"SELECT * FROM {options.table_name} WHERE drive_file_id IN ({placeholders}) {options.get_full_filter_sql()}"
		rows = cls._execute_query(query, files_ids)
		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_from_category(cls, category: Category, options: FileQueryOptions = None) -> list['File']:
		"""
		Retrieves all files (including folders) associated with a given category.

		:param options:
		:param category: Category object to fetch files from.
		:return: List of File objects.
		"""
		if category is None or category.id is None:
			logger.error("Category object or its ID cannot be None.")
			return []

		options = options if options else FileQueryOptions()

		query = f"""
        SELECT f.* FROM {options.table_name}
        JOIN file_categories fc ON f.id = fc.file_id 
        WHERE fc.category_id = ? {options.get_full_filter_sql()};
        """
		# Używamy category.id jako parametru zapytania
		rows = cls._execute_query(query, (category.id,))
		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_files_from_folders(cls, folders: list['File'], options: FileQueryOptions = None) -> list['File']:
		"""
		Retrieves direct children of the given parent folders.
		:param options:
		:param folders: List of parent folders.
		"""
		if not folders:
			return []
		options = options if options else FileQueryOptions()
		placeholders = ','.join('?' for _ in folders)
		query = f"SELECT * FROM {options.table_name} WHERE parent_id IN ({placeholders}) {options.get_full_filter_sql()}"
		rows = cls._execute_query(query, [folder.drive_file_id for folder in folders])
		return [cls(**dict(row)) for row in rows]

	@classmethod
	def get_files_from_category_type(cls, category_type: CategoryType, options: FileQueryOptions = None) -> list[
		'File']:
		"""Retrieves all files associated with a given category type."""
		options = options if options else FileQueryOptions()
		query = f"""
        SELECT f.* FROM category_types ct
        JOIN categories c ON c.category_type_id = ct.id
        JOIN file_categories fc ON fc.category_id = c.id
        JOIN {options.table_name} ON f.id = fc.file_id
        WHERE ct.name = '{category_type.name}' {options.get_full_filter_sql()}
        ORDER BY f.name;
        """
		rows = cls._execute_query(query)
		return [File(**dict(row)) for row in rows]

	@classmethod
	def get_root_folders(cls, options: FileQueryOptions = None) -> list['File']:
		"""Retrieves top-level folders (folders without a parent)."""
		options = options or FileQueryOptions(folder_only=True)
		query = f"SELECT * FROM {options.table_name} WHERE parent_id IS NULL {options.get_full_filter_sql()}"
		rows = cls._execute_query(query)
		return [cls(**dict(row)) for row in rows]

	def get_created_date(self) -> str:
		"""Returns the creation or modification date of the file."""
		date_only = self.created_time.split('T')[0]
		return date_only

	def child_of(self, folder: 'File') -> int:
		"""Checks if this file is a child of another folder.
		:param folder: The folder to check against.
		:return: Distance from the folder: -1 = not a child, 0 = same file, 1 = direct child, 2 = grandchild, etc.
		"""

		distance = 0
		current_file = self
		while current_file and current_file.parent_id is not None:
			if current_file.drive_file_id == folder.drive_file_id:
				return distance
			current_file = File.get_files_by_ids([current_file.parent_id])[0]
			distance += 1
		return -1

	@classmethod
	def get_from_list_by_name(cls, files_list: list['File'], name_to_find: str) -> list['File']:
		"""
		Filters a list of File objects, returning those with a matching name.
		:param files_list: List of File objects to search.
		:param name_to_find: Name of the file to find.
		:return: Filtered list of File objects.
		"""
		if not files_list or not name_to_find:
			return []

		return [f for f in files_list if f.name == name_to_find]

	@classmethod
	def get_all(cls, options: FileQueryOptions = None) -> list['File']:
		"""Retrieves all files from the database."""
		options = options if options else FileQueryOptions()
		query = f"SELECT * FROM {options.table_name} where {options.get_full_filter_sql(False)}"
		rows = cls._execute_query(query)
		return [cls(**dict(row)) for row in rows]

	def __repr__(self):
		return f"<File(id={self.id}, name='{self.name}', type='{self.mime_type}')>"
