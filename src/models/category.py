import sqlite3

from main import logger
from src.models.base_model import BaseModel
from src.models.category_type import CategoryType
from src.db.database import get_db_connection


class Category(BaseModel):
	_table_name = 'categories'

	def __init__(self, id=None, category_type_id=None, canonical_name=None):
		super().__init__(id=id, category_type_id=category_type_id, canonical_name=canonical_name)
		self.id = id
		self.category_type_id = category_type_id
		self.canonical_name = canonical_name

	@classmethod
	def find_or_create(cls, category_type_id, canonical_name):
		"""Fetches a category by canonical name and type, or creates a new one."""
		conn = get_db_connection()
		c = conn.cursor()
		try:
			c.execute(
				"SELECT id, category_type_id, canonical_name FROM categories WHERE category_type_id = ? AND canonical_name = ?",
				(category_type_id, canonical_name))
			row = c.fetchone()
			if row:
				return cls(**dict(row))
			else:
				c.execute("INSERT INTO categories (category_type_id, canonical_name) VALUES (?, ?)",
						  (category_type_id, canonical_name))
				conn.commit()
				return cls(id=c.lastrowid, category_type_id=category_type_id, canonical_name=canonical_name)
		finally:
			conn.close()

	@classmethod
	def get_by_type(cls, category_type: CategoryType):
		"""
		Fetches all categories associated with a given category type.

		:param category_type: CategoryType object.
		:return: List of Category objects.
		"""

		query = f"""
        SELECT c.*
        FROM {cls._table_name} c
        JOIN category_types ct ON c.category_type_id = ct.id
        WHERE ct.name = ?;
        """
		rows = cls._execute_query(query, (category_type.name,))
		return [cls(**dict(row)) for row in rows]

	# def get_all_lower_categories_from_category_type(self, category_type: CategoryType):
	#     """
	#     Fetches all categories of a given type that have file representations in this category.
	#
	#     :param category_type: CategoryType object.
	#     :return: List of Category objects.
	#     """
	#
	#     query = f"""
	#     select DISTINCT c2.id, c2.category_type_id, c2.canonical_name
	#     from {self._table_name} c
	#     join category_types ct on c.category_type_id = ct.id
	#     join category_aliases ca on c.id = ca.category_id
	#     join files f on f.name = ca.alias_name
	#     join files ff on ff.parent_id = f.drive_file_id
	#     join category_aliases ca2 on ff.name = ca2.alias_name
	#     join categories c2 on ca2.category_id = c2.id
	#     join category_types ct2 on c2.category_type_id = ct2.id
	#     where ct.id = ? -- Upper category type
	#     and c.id = ?
	#     and ct2.id = ? -- Lower category type
	#     ORDER by ff.name;
	#     """
	#     rows = self._execute_query(query, (self.category_type_id, self.id, category_type.id))
	#     return [Category(**dict(row)) for row in rows]

	def __repr__(self):
		return f"<Category(id={self.id}, name='{self.canonical_name}')>"

	def link_file(self, file_id, temp: bool = False):
		"""Links this category to a given file."""

		table_name = "file_categories_temp" if temp else "file_categories"
		query = f"INSERT OR IGNORE INTO {table_name} (file_id, category_id) VALUES (?, ?)"

		link = self._execute_query(query, (file_id, self.id))
		return link is not None

	def delete(self):
		"""
		Deletes all categories associated with this category type.

		:return: True if deleted, False otherwise.
		"""

		query = f"""
        DELETE FROM {self._table_name}
        WHERE category_type_id = ?;
        """

		rows_deleted = self._execute_query(query, (self.category_type_id,), commit=True)
		return rows_deleted is not None

	@classmethod
	def replace_links(cls):
		"""Replaces temporary file links in the database."""
		conn = get_db_connection()
		try:
			with conn:
				conn.execute("DELETE FROM file_categories;")

				conn.execute("""
                        INSERT OR IGNORE INTO file_categories (file_id, category_id)
                        SELECT file_id, category_id FROM file_categories_temp;
                    """)

				conn.execute("DELETE FROM file_categories_temp;")
		except Exception as e:
			logger.error(f"Unexpected error occurred while replacing file links: {e}")
			raise
