#!/usr/bin/env python3
# ui/mobsf_ui_manager.py - MobSF integration UI management

import logging
import os
from typing import Optional

import requests
from PySide6.QtCore import QObject, QProcess, Signal, Slot


class MobSFUIManager(QObject):
    """Manages MobSF integration for the Appium Crawler Controller UI."""
    
    def __init__(self, main_controller):
        """
        Initialize the MobSF UI manager.
        
        Args:
            main_controller: The main UI controller
        """
        super().__init__()
        self.main_controller = main_controller
        self.config = main_controller.config
        self.api_dir = self.config.BASE_DIR
        self.mobsf_test_process: Optional[QProcess] = None
    
    @Slot()
    def test_mobsf_connection(self):
        """Test the connection to the MobSF server."""
        # Check if MobSF analysis is enabled
        if not self.main_controller.config_widgets['ENABLE_MOBSF_ANALYSIS'].isChecked():
            self.main_controller.log_message("Error: MobSF Analysis is not enabled. Please enable it in settings.", 'red')
            return
            
        self.main_controller.log_message("Testing MobSF connection...", 'blue')
        api_url = self.main_controller.config_widgets['MOBSF_API_URL'].text().strip()
        api_key = self.main_controller.config_widgets['MOBSF_API_KEY'].text().strip()

        if not api_url or not api_key:
            self.main_controller.log_message("Error: MobSF API URL and API Key are required.", 'red')
            return

        headers = {'Authorization': api_key}
        
        # Use the /scans endpoint to get recent scans, which is a good way to test the connection
        test_url = f"{api_url.rstrip('/')}/scans"
        
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            if response.status_code == 200:
                self.main_controller.log_message("MobSF connection successful!", 'green')
                logging.info(f"MobSF server response: {response.json()}")
            else:
                self.main_controller.log_message(f"MobSF connection failed with status code: {response.status_code}", 'red')
                self.main_controller.log_message(f"Response: {response.text}", 'red')
        except requests.RequestException as e:
            self.main_controller.log_message(f"MobSF connection error: {e}", 'red')

        logging.debug(f"MobSF API URL used: {test_url}")
        # Redundant tips removed from UI log for cleaner interface


# Import here to avoid circular imports
import sys
