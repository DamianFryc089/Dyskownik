class FileQueryOptions:
	"""
	Class storing filtering options for file queries.
	"""

	def __init__(self, folder_only: bool = False, exclude_shortcuts: bool = True, temp: bool = False,
				 active_only: bool = True):
		self.folder_only = folder_only
		self.exclude_shortcuts = exclude_shortcuts
		self.table_name = "files_temp f" if temp else "files f"
		self.active_only = active_only

	def get_mime_filter_sql(self) -> str:
		"""Returns the SQL fragment for filtering by MIME type (folders only)."""
		return " f.mime_type = 'application/vnd.google-apps.folder'" if self.folder_only else ""

	def get_shortcut_filter_sql(self) -> str:
		"""Returns the SQL fragment for excluding shortcuts."""
		return " f.mime_type != 'application/vnd.google-apps.shortcut'" if self.exclude_shortcuts else ""

	def get_active_filter_sql(self) -> str:
		"""Returns the SQL fragment for filtering active records."""
		return "active = 1" if self.active_only else ""

	def get_full_filter_sql(self, start_with_and=True) -> str:
		"""Returns the full SQL fragment for all applied filters."""
		filters = [
			self.get_mime_filter_sql(),
			self.get_shortcut_filter_sql(),
			self.get_active_filter_sql()
		]

		# Remove empty strings from the list
		valid_filters = [f for f in filters if f]
		beginning = " AND " if start_with_and and valid_filters else ""
		return (beginning + " AND ".join(valid_filters)) if valid_filters else ""
