import sqlite3
import re

from main import logger


def get_db_connection():
	from main import config_data
	"""Returns a database connection object."""
	conn = sqlite3.connect(config_data.database_file)
	conn.row_factory = sqlite3.Row  # Enable named column access
	conn.create_function("REGEXP", 2, regexp)
	return conn


def close_db_connection(conn):
	"""Closes the database connection."""
	if conn:
		conn.close()


def regexp(expression_with_flags, item):
	if item is None:
		return False

	match = re.match(r'^/(.*?)/([gmi]*)$', expression_with_flags)
	if match:
		pattern = match.group(1)
		flags_str = match.group(2)
	else:
		pattern = expression_with_flags
		flags_str = ''

		regex_metachars_to_check = r'[.^$*+?{}\[\]\\|()]'

		if not (pattern.startswith('^') or pattern.endswith('$') or re.search(regex_metachars_to_check, pattern)):
			pattern = '^' + re.escape(pattern) + '$'

	re_flags = 0
	if 'i' in flags_str:
		re_flags |= re.IGNORECASE

	return re.match(pattern, item, re_flags) is not None


def setup_database():
	"""Set up the database by creating necessary tables if they do not exist."""

	from main import config_data
	conn = None
	try:
		conn = sqlite3.connect(config_data.database_file)
		c = conn.cursor()
		c.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_file_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                parent_id TEXT,
                owner TEXT,
                created_time TEXT,
                modified_time TEXT,
                size INTEGER,
                shortcut_target_id TEXT,
                md5_checksum TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS category_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                aggregation_type TEXT NOT NULL
            )
        ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_type_id INTEGER NOT NULL,
                canonical_name TEXT NOT NULL,
                FOREIGN KEY (category_type_id) REFERENCES category_types(id) ON DELETE CASCADE
            )
        ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS category_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                alias_name TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS file_categories (
                file_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (file_id, category_id),
                FOREIGN KEY (file_id) REFERENCES files(id),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS files_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_file_id TEXT UNIQUE NOT NULL,
                name TEXT,
                mime_type TEXT,
                parent_id TEXT,
                owner TEXT,
                created_time TEXT,
                modified_time TEXT,
                size INTEGER,
                shortcut_target_id TEXT,
                md5_checksum TEXT,
                active INTEGER DEFAULT 1
            )
            ''')
		c.execute('''
            CREATE TABLE IF NOT EXISTS file_categories_temp (
                file_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (file_id, category_id)
            )
            ''')

		c.execute('''
            CREATE TABLE IF NOT EXISTS drive_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                drive_file_id TEXT UNIQUE NOT NULL,
                parent_id TEXT,
                shortcut_target_id TEXT,
                category_type_id INTEGER,
                level INTEGER NOT NULL
            )
            ''')

		conn.commit()
	except sqlite3.Error as e:
		logger.error(f"Error during database setup: {e}")
		if conn:
			conn.rollback()
	finally:
		if conn:
			conn.close()


def drop_database():
	from main import config_data
	conn = None
	try:
		conn = sqlite3.connect(config_data.database_file)
		c = conn.cursor()
		c.execute('DROP TABLE IF EXISTS files')
		c.execute('DROP TABLE IF EXISTS category_types')
		c.execute('DROP TABLE IF EXISTS categories')
		c.execute('DROP TABLE IF EXISTS category_aliases')
		c.execute('DROP TABLE IF EXISTS file_categories')
		c.execute('DROP TABLE IF EXISTS files_temp')
		c.execute('DROP TABLE IF EXISTS file_categories_temp')
		c.execute('DROP TABLE IF EXISTS drive_files')
		conn.commit()
	except sqlite3.Error as e:
		logger.error(f"Error during database drop: {e}")
		if conn:
			conn.rollback()
	finally:
		if conn:
			conn.close()
