from src.models.base_model import BaseModel
from src.models.category_type import CategoryType
from src.models.file import File


class DriveFile(BaseModel):
	_table_name = 'drive_files'

	def __init__(self, id: int = None, name: int = None, category_type_id: int = None, level: int = None,
				 drive_file_id: str = None, parent_id: str = None,
				 shortcut_target_id: str = None):
		super().__init__()
		self.id = id
		self.name = name
		self.category_type_id = category_type_id
		self.level = level
		self.drive_file_id = drive_file_id
		self.parent_id = parent_id
		self.shortcut_target_id = shortcut_target_id

	@classmethod
	def add_drive_file(cls, file: File, level: int, category_type: CategoryType = None) -> None:
		"""Adds a new drive file entry to the database."""
		query = f"""
            INSERT INTO {cls._table_name} (name, drive_file_id, parent_id, shortcut_target_id, category_type_id, level)
            VALUES (?, ?, ?, ?, ?, ?)
        """
		category_type_id = category_type.id if category_type else None
		cls._execute_query(query, (
		file.name, file.drive_file_id, file.parent_id, file.shortcut_target_id, category_type_id, level), commit=True)

	@classmethod
	def delete_by_category_type(cls, category_type: CategoryType) -> None:
		"""Deletes all drive files associated with a specific category type."""
		query = f"DELETE FROM {cls._table_name} WHERE category_type_id = ?"
		cls._execute_query(query, (category_type.id,), commit=True)

	@classmethod
	def get_all_drive_files(cls) -> list['DriveFile']:
		"""Fetches all drive files from the database."""
		query = f"SELECT * FROM {cls._table_name}"
		rows = cls._execute_query(query)
		return [DriveFile(**dict(row)) for row in rows]

	@classmethod
	def get_drive_files_by_level(cls, level: int, category_type: CategoryType = None, parent_id: str = None) -> list[
		'DriveFile']:
		"""Fetches all drive files at a specific level."""

		if category_type is None:
			query = f"SELECT * FROM {cls._table_name} WHERE level = ? AND category_type_id IS NULL"
			params = (level,)
		else:
			if parent_id is None:
				query = f"SELECT * FROM {cls._table_name} WHERE level = ? AND category_type_id = ?"
				params = (level, category_type.id)
			else:
				query = f"SELECT * FROM {cls._table_name} WHERE level = ? AND category_type_id = ? AND parent_id = ?"
				params = (level, category_type.id, parent_id)

		rows = cls._execute_query(query, params)
		return [DriveFile(**dict(row)) for row in rows]

	def delete(self) -> None:
		"""Deletes this drive file from the database."""
		query = f"DELETE FROM {self._table_name} WHERE id = ?"
		self._execute_query(query, (self.id,), commit=True)

	@classmethod
	def delete_all(cls, skip_root: bool = False) -> None:
		"""Deletes all drive files from the database."""
		query = f"DELETE FROM {cls._table_name} {'WHERE level > 0' if skip_root else ''}"
		cls._execute_query(query, commit=True)

	def __repr__(self):
		return f"DriveFile(id={self.id}, name='{self.name}', category_type_id={self.category_type_id})"
