"""
Service for OneDrive/SharePoint integration using Microsoft Graph API
"""

import os
import json
import logging
import requests
import msal
from flask import url_for, session, redirect, request, current_app
from datetime import datetime

logger = logging.getLogger(__name__)

class OneDriveService:
    """Service for OneDrive/SharePoint integration"""

    def __init__(self, app=None):
        """Initialize the OneDrive service"""
        self.app = app
        self.client_id = None
        self.client_secret = None
        self.tenant_id = None
        self.redirect_uri = None
        self.scopes = ["Files.ReadWrite", "Sites.ReadWrite.All"]
        self.authority = None
        self.graph_api_endpoint = "https://graph.microsoft.com/v1.0"

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the service with Flask app"""
        self.app = app
        self.client_id = app.config.get('MICROSOFT_CLIENT_ID')
        self.client_secret = app.config.get('MICROSOFT_CLIENT_SECRET')
        self.tenant_id = app.config.get('MICROSOFT_TENANT_ID')
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Register routes
        app.add_url_rule('/onedrive/auth', 'onedrive_auth', self.auth)
        app.add_url_rule('/onedrive/callback', 'onedrive_callback', self.callback)

        # Log configuration
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            logger.warning("OneDrive integration not fully configured. Missing credentials.")

    def _build_msal_app(self):
        """Build the MSAL application for authentication"""
        return msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )

    def _get_token_from_cache(self):
        """Get token from session cache"""
        if 'onedrive_token_cache' in session:
            cache = msal.SerializableTokenCache()
            cache.deserialize(session['onedrive_token_cache'])

            accounts = self._build_msal_app().get_accounts()
            if accounts:
                result = self._build_msal_app().acquire_token_silent(
                    self.scopes,
                    account=accounts[0]
                )
                return result
        return None

    def auth(self):
        """Initiate the authentication flow"""
        # Build the app
        app = self._build_msal_app()

        # Get the authorization URL
        auth_url = app.get_authorization_request_url(
            self.scopes,
            redirect_uri=url_for('onedrive_callback', _external=True),
            state=json.dumps({'next': request.args.get('next', '/')})
        )

        return redirect(auth_url)

    def callback(self):
        """Handle the authentication callback"""
        # Get the state
        state = json.loads(request.args.get('state', '{}'))
        next_url = state.get('next', '/')

        # Get the authorization code
        code = request.args.get('code')

        if not code:
            logger.error("No authorization code received from Microsoft")
            return redirect(next_url)

        # Build the app
        app = self._build_msal_app()

        # Get the token
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=self.scopes,
            redirect_uri=url_for('onedrive_callback', _external=True)
        )

        if 'error' in result:
            logger.error(f"Error getting token: {result.get('error_description')}")
            return redirect(next_url)

        # Save the token in the session
        cache = msal.SerializableTokenCache()
        if 'onedrive_token_cache' in session:
            cache.deserialize(session['onedrive_token_cache'])

        cache.add(result)
        session['onedrive_token_cache'] = cache.serialize()

        return redirect(next_url)

    def is_authenticated(self):
        """Check if the user is authenticated with OneDrive"""
        token = self._get_token_from_cache()
        return token is not None

    def upload_file(self, file_data, filename, folder_path=None):
        """
        Upload a file to OneDrive/SharePoint

        Args:
            file_data: The file data to upload
            filename: The name of the file
            folder_path: Optional folder path in OneDrive/SharePoint

        Returns:
            dict: Response from the API with file details
        """
        token = self._get_token_from_cache()

        if not token:
            logger.error("No valid token found for OneDrive upload")
            return {'error': 'Authentication required'}

        # Determine the upload path
        upload_path = f"/me/drive/root:/{filename}:/content"
        if folder_path:
            upload_path = f"/me/drive/root:/{folder_path}/{filename}:/content"

        # Upload the file
        headers = {
            'Authorization': f"Bearer {token['access_token']}",
            'Content-Type': 'application/octet-stream'
        }

        response = requests.put(
            f"{self.graph_api_endpoint}{upload_path}",
            headers=headers,
            data=file_data
        )

        if response.status_code in (200, 201):
            logger.info(f"File {filename} uploaded successfully to OneDrive")
            return response.json()
        else:
            logger.error(f"Error uploading file to OneDrive: {response.text}")
            return {'error': response.text}

    def get_sharepoint_url(self):
        """
        Get the SharePoint URL from system settings

        Returns:
            str: The SharePoint URL or default URL if not set
        """
        try:
            from models import SystemSettings
            from flask import current_app

            # Get the SharePoint URL from system settings
            setting = SystemSettings.query.filter_by(key='sharepoint_url').first()

            if setting and setting.value:
                return setting.value
            else:
                # Return default URL if not set
                return "https://cpcholding0.sharepoint.com/:f:/s/SacodecoHousing/EhzAcv7ftdZOiv2VX3yihO4BFUObApyWXfMoeXUV4OLCvg?e=UAmx11"
        except Exception as e:
            logger.error(f"Error getting SharePoint URL from settings: {str(e)}")
            # Return default URL if error
            return "https://cpcholding0.sharepoint.com/:f:/s/SacodecoHousing/EhzAcv7ftdZOiv2VX3yihO4BFUObApyWXfMoeXUV4OLCvg?e=UAmx11"

    def get_shared_link(self, file_id, type='view'):
        """
        Get a shareable link for a file

        Args:
            file_id: The ID of the file
            type: The type of link (view, edit)

        Returns:
            str: The shareable link
        """
        token = self._get_token_from_cache()

        if not token:
            logger.error("No valid token found for getting shared link")
            return None

        # Create sharing link
        headers = {
            'Authorization': f"Bearer {token['access_token']}",
            'Content-Type': 'application/json'
        }

        data = {
            'type': type,
            'scope': 'organization'
        }

        response = requests.post(
            f"{self.graph_api_endpoint}/me/drive/items/{file_id}/createLink",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            result = response.json()
            return result.get('link', {}).get('webUrl')
        else:
            logger.error(f"Error getting shared link: {response.text}")
            return None
