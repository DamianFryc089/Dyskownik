import http.client as http_client
import logging
import socket

import googleapiclient
import httplib2
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from enum import Enum

from main import logger
from src.models.file import File

# --- Configuration ---
credentials_file = 'credentials.json'

# --- Retry Exceptions ---
RETRYABLE_EXCEPTIONS = (
	googleapiclient.errors.HttpError,
	googleapiclient.errors.ResumableUploadError,
	http_client.IncompleteRead,
	socket.gaierror
)

DEFAULT_HTTP_TIMEOUT = 30


# --- NEW: Enum for Drive Scope Modes ---
class DriveScopeMode(Enum):
	"""
	Defines the available Google Drive API scope modes.
	"""
	READ_ONLY = 'readonly'
	DRIVE_FILE = 'drive.file'
	DRIVE = 'drive'


class DriveAPIClient:
	"""
	Manages API call execution with retry logic.
	Does NOT hold the service object itself for thread-safety reasons;
	the service object is passed into its methods.
	"""
	# Map Enum members to their corresponseing Google API scope URLs
	SCOPE_URL_MAPPING = {
		DriveScopeMode.READ_ONLY: ['https://www.googleapis.com/auth/drive.metadata.readonly'],
		DriveScopeMode.DRIVE_FILE: ['https://www.googleapis.com/auth/drive.file'],
		DriveScopeMode.DRIVE: ['https://www.googleapis.com/auth/drive']
	}

	def __init__(self):
		pass

	@retry(
		stop=stop_after_attempt(5),
		wait=wait_exponential(multiplier=1, min=4, max=10),
		retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS)
	)
	def _execute_api_call_with_retry(self, api_call, error_entity_id: str, error_entity_type: str) -> dict:
		"""
		Executes a Google Drive API call with a retry mechanism.
		"""
		try:
			response = api_call.execute()
			return response
		except googleapiclient.errors.HttpError as e:
			if e.resp.status == 404:
				logger.warning(
					f"Could not find {error_entity_type} with ID {error_entity_id} or no permissions. "
					f"Status: {e.resp.status}"
				)
				return {}
			elif e.resp.status == 403:
				logger.error(
					f"Permission denied for {error_entity_type} with ID {error_entity_id}. "
					f"Status: {e.resp.status}"
				)
				return {}
			else:
				logger.error(
					f"HTTP Error ({e.resp.status}) while fetching {error_entity_type} {error_entity_id}. "
					"Retrying...", exc_info=True
				)
				raise

	def fetch_file_data(self, service_instance: googleapiclient.discovery.Resource, file_id: str) -> File:
		"""
		Fetches metadata for a single file or folder from Google Drive using a given service instance.
		"""
		api_request = service_instance.files().get(
			fileId=file_id,
			fields="id, name, mimeType, parents, owners, createdTime, modifiedTime, size, shortcutDetails, md5Checksum",
			supportsAllDrives=True
		)
		response = self._execute_api_call_with_retry(api_request, file_id, "fetch: file")
		return File.from_api_response(response) if response else None

	def fetch_folder_data(self, service_instance: googleapiclient.discovery.Resource, folder_id: str,
						  page_token: str = None) -> dict[str, list[File]]:
		"""
		Lists contents (files and subfolders) within a given Google Drive folder using a given service instance.
		"""
		query = f"'{folder_id}' in parents"
		api_request = service_instance.files().list(
			q=query,
			pageSize=500,
			fields="files(id, name, mimeType, parents, owners, createdTime, modifiedTime, size, shortcutDetails), nextPageToken",
			supportsAllDrives=True,
			includeItemsFromAllDrives=True,
			pageToken=page_token
		)

		response = self._execute_api_call_with_retry(api_request, folder_id, "fetch: folder")
		if not response:
			return {}

		files: list[File] = []
		for file in response.get('files', []):
			file_obj = File.from_api_response(file)
			files.append(file_obj)

		return {
			'files': files,
			'nextPageToken': response.get('nextPageToken')
		}

	def create_drive_folder(self, service_instance: googleapiclient.discovery.Resource, folder_name: str,
							parent_folder_id: str) -> File:
		file_metadata = {
			'name': folder_name,
			'mimeType': 'application/vnd.google-apps.folder'
		}
		if parent_folder_id:
			file_metadata['parents'] = [parent_folder_id]

		api_request = service_instance.files().create(
			body=file_metadata,
			fields="id, name, mimeType, parents, owners, createdTime, modifiedTime, size, md5Checksum",
			supportsAllDrives=True
		)
		response = self._execute_api_call_with_retry(api_request, folder_name, 'create: folder')
		return File.from_api_response(response) if response else None

	def create_drive_shortcut(self, service_instance: googleapiclient.discovery.Resource, shortcut_name: str,
							  target_id: str, parent_folder_id: str) -> File:
		file_metadata = {
			'name': shortcut_name,
			'mimeType': 'application/vnd.google-apps.shortcut',
			'shortcutDetails': {
				'targetId': target_id
			}
		}
		if parent_folder_id:
			file_metadata['parents'] = [parent_folder_id]

		api_request = service_instance.files().create(
			body=file_metadata,
			fields="id, name, mimeType, parents, owners, createdTime, modifiedTime, size, shortcutDetails, md5Checksum",
			supportsAllDrives=True
		)
		response = self._execute_api_call_with_retry(api_request, shortcut_name, 'create: shortcut')
		return File.from_api_response(response) if response else None

	def remove_drive_file(self, service_instance: googleapiclient.discovery.Resource, file_id: str):
		"""
		Deletes a Google Drive shortcut by its ID.
		"""
		api_request = service_instance.files().delete(
			fileId=file_id,
			supportsAllDrives=True
		)
		return self._execute_api_call_with_retry(api_request, file_id, 'remove: file')

	@staticmethod
	def get_credentials(scope_mode: DriveScopeMode = DriveScopeMode.READ_ONLY) -> Credentials:
		"""
		Handles Google Drive API authentication and returns user credentials.
		The 'scope_mode' parameter determines the level of access requested.

		:param scope_mode: A member of the DriveScopeMode Enum (e.g., DriveScopeMode.READ_ONLY).
		:return: Authenticated Credentials object.
		:raises ValueError: If an invalid scope_mode is provided (though type hinting helps prevent this).
		:raises Exception: If authentication fails.
		"""
		if scope_mode not in DriveAPIClient.SCOPE_URL_MAPPING:
			raise ValueError(
				f"Invalid scope_mode: '{scope_mode}'. Choose from {list(DriveAPIClient.SCOPE_URL_MAPPING.keys())}.")

		target_scopes = DriveAPIClient.SCOPE_URL_MAPPING[scope_mode]
		# Use the Enum value (string) for the token file name for clarity and uniqueness
		token_file = f'token_{scope_mode.value}.json'

		creds = None
		try:
			creds = Credentials.from_authorized_user_file(token_file, target_scopes)
			logger.info(f"Loaded credentials from {token_file} for scope_mode: '{scope_mode.value}'")
		except Exception as e:
			logger.warning(
				f"Could not load {token_file}, initiating new auth flow for scope_mode: '{scope_mode.value}': {e}")
			try:
				flow = InstalledAppFlow.from_client_secrets_file(credentials_file, target_scopes)
				creds = flow.run_local_server(port=0)
				with open(token_file, 'w') as token:
					token.write(creds.to_json())
				logger.info(
					f"Successfully obtained and saved new credentials to {token_file} for scope_mode: '{scope_mode.value}'.")
			except Exception as auth_e:
				logger.critical(
					f"Failed to authenticate with Google Drive API for scope_mode '{scope_mode.value}': {auth_e}",
					exc_info=True)
				logger.critical("Cannot proceed without valid Google Drive API credentials.")
				raise

		return creds

	@staticmethod
	def create_drive_service(creds):
		http = AuthorizedHttp(creds, http=httplib2.Http(timeout=DEFAULT_HTTP_TIMEOUT))
		service = build(
			'drive',
			'v3',
			http=http,
			cache_discovery=False
		)
		return service
