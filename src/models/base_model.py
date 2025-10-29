from src.db.database import get_db_connection


class BaseModel:
	_table_name = None

	def __init__(self, **kwargs):
		# Dynamically set attributes from kwargs
		for key, value in kwargs.items():
			setattr(self, key, value)

	def to_dict(self):
		"""Converts the model instance to a dictionary."""
		# Get all public instance attributes
		# You might need to refine this to exclude certain internal attributes
		return {
			key: value for key, value in self.__dict__.items()
			if not key.startswith('_')  # Exclude attributes starting with _
		}

	@classmethod
	def _execute_query(cls, query, params=(), fetch_one=False, commit=True):
		"""Helper method to execute database queries."""
		conn = get_db_connection()
		c = conn.cursor()
		c.execute("PRAGMA foreign_keys=ON;")
		try:
			c.execute(query, params)
			if commit:
				conn.commit()
			if fetch_one:
				return c.fetchone()
			else:
				return c.fetchall()
		finally:
			conn.close()

	@classmethod
	def find_by_id(cls, obj_id):
		"""Fetches an object by its ID."""
		if not cls._table_name:
			raise NotImplementedError("Table name not defined for this model.")
		query = f"SELECT * FROM {cls._table_name} WHERE id = ?"
		row = cls._execute_query(query, (obj_id,), fetch_one=True)
		return cls(**dict(row)) if row else None

	@classmethod
	def all(cls):
		"""Fetches all records from the table."""
		if not cls._table_name:
			raise NotImplementedError("Table name not defined for this model.")
		query = f"SELECT * FROM {cls._table_name}"
		rows = cls._execute_query(query)
		return [cls(**dict(row)) for row in rows]
