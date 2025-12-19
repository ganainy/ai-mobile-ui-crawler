# ui/device_manager.py - Handles device detection and UI dropdown population

import logging
from typing import List, Optional
from PySide6.QtWidgets import QComboBox
from infrastructure.device_detection import detect_all_devices

class DeviceManager:
    """Handles device detection and UI dropdown population."""
    
    def __init__(self, device_dropdown: QComboBox, config, log_callback):
        self.device_dropdown = device_dropdown
        self.config = config
        self.log_callback = log_callback
        
    def populate_devices(self):
        """Populate the device dropdown with connected devices."""
        self.log_callback("Refreshing connected devices...", "blue")
        
        if not self.device_dropdown:
            return

        try:
            devices = detect_all_devices()
            self.device_dropdown.clear()

            if devices:
                device_ids = [d.id for d in devices]
                self.device_dropdown.addItems(device_ids)
                self.log_callback(f"Found devices: {', '.join(device_ids)}", "green")
                
                # Try to restore selection
                current_udid = self.config.get("TARGET_DEVICE_UDID", None)
                if current_udid:
                    index = self.device_dropdown.findText(current_udid)
                    if index != -1:
                        self.device_dropdown.setCurrentIndex(index)
                        return
                        
                # Auto-select first
                self.device_dropdown.setCurrentIndex(0)
                self.config.update_setting_and_save("TARGET_DEVICE_UDID", device_ids[0])
                self.log_callback(f"Auto-selected device UDID: {device_ids[0]}", "blue")
            else:
                self.device_dropdown.addItem("No devices found")
                self.log_callback("No connected devices found.", "orange")
                self.config.update_setting_and_save("TARGET_DEVICE_UDID", None)
                
        except Exception as e:
            self.log_callback(f"Error refreshing devices: {e}", "red")
            logging.error(f"Error populating devices: {e}", exc_info=True)
