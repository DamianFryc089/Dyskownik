import json

from main import logger
from src.models.file import File

opened = list()


def append_to_json(data: list, filename: str) -> None:
	"""
	Save data to a JSON file.

	:param data: Data to be saved. List of objects.
	:param filename: Name of the file to save the data to.
	"""
	if filename not in opened:
		with open(filename, 'w', encoding='utf-8') as f:
			f.write('[\n')
		opened.append(filename)
	else:
		with open(filename, "rb+") as f:
			f.seek(-3, 2)
			f.truncate()
			f.write(b",\n")

	with open(filename, "a", encoding="utf-8") as f:
		first = True
		for item in data:
			if not first:
				f.write(",\n")
			if isinstance(item, File):
				item = item.to_dict()
			json_line = json.dumps(item, indent=4, ensure_ascii=False)
			f.write(json_line)
			first = False
		f.write("\n]")


def save_aliases_to_json(data, file_name: str = 'category_aliases.json') -> None:
	"""
	Save data to a JSON file. If the file already exists, it appends the data in JSON format.

	:param data: Data to be saved. List of objects.
	:param file_name: Name of the file to save the data to. If None, defaults to category_aliases.json.
	"""

	json_data = {
		"category_type_name": "category_type_name",
		"aggregation_type": "aggregation_type",
		"categories": [
			{
				"canonical_name": "Example1",
				"aliases": ["Example1", "example1", "example 1"]
			}
		],
		"unassigned_folders": data
	}
	try:
		with open(file_name, "w", encoding="utf-8") as f:
			f.write(json.dumps(json_data, indent=4, ensure_ascii=False))
	except IOError as e:
		logger.error(f"Error with saving '{file_name}': {e}")


def get_json(json_file):
	try:
		with open(json_file, 'r', encoding='utf-8') as f:
			data = json.load(f)
	except json.JSONDecodeError as e:
		logger.error(f"Error parsing JSON file '{json_file}': {e}")
		return None
	except FileNotFoundError:
		logger.error(f"File '{json_file}' not found.")
		return None
	except IOError as e:
		logger.error(f"Error reading file '{json_file}': {e}")
		return None
	except Exception as e:
		logger.error(f"An unexpected error occurred while reading '{json_file}': {e}")
		return None
	return data


def get_lines_from_file(filename: str, first_word_only: bool = False) -> list[str]:
	"""
	Get lines from a file. Line is considered valid if it is not empty and does not start with whitespace.

	:param filename: Name of the file to read lines from.
	:param first_word_only: If True, only the first word of each line is kept.
	:return: List of lines.
	"""
	lines = []
	try:
		with open(filename, 'r', encoding='utf-8') as f:
			for line in f:
				if line:
					if line.startswith(' '):
						continue
					if first_word_only:
						line = line.split()[0]
					lines.append(line)
	except FileNotFoundError:
		logger.error(f"File '{filename}' not found.")
	return lines
