import sqlite3

from src.models.base_model import BaseModel
from src.db.database import get_db_connection
from src.models.category import Category


class CategoryAlias(BaseModel):
	_table_name = 'category_aliases'

	def __init__(self, id=None, category_id=None, alias_name=None):
		super().__init__(id=id, category_id=category_id, alias_name=alias_name)
		self.id = id
		self.category_id = category_id
		self.alias_name = alias_name

	@classmethod
	def find_or_create(cls, category_id, alias_name):
		"""Retrieves a category alias by category ID and alias name, or creates a new one."""
		query_select = "SELECT id, category_id, alias_name FROM category_aliases WHERE category_id = ? AND alias_name = ?"
		row = cls._execute_query(query_select, (category_id, alias_name), fetch_one=True)
		if row:
			return cls(**dict(row))

		query = "INSERT OR IGNORE INTO category_aliases (category_id, alias_name) VALUES (?, ?)"
		row = cls._execute_query(query, (category_id, alias_name), commit=True)
		return cls(**dict(row))

	@classmethod
	def get_by_category(cls, category: Category):
		"""Retrieves all aliases for the category."""
		query = "SELECT * FROM category_aliases WHERE category_id = ?"
		rows = cls._execute_query(query, (category.id,))
		return [CategoryAlias(**dict(row)) for row in rows]

	def __repr__(self):
		return f"<CategoryAlias(id={self.id}, alias='{self.alias_name}', category_id={self.category_id})>"
