
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options

def test_connection():
    print("Connecting to device...")
    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.device_name = '279cb9b1'
    options.automation_name = 'UiAutomator2'
    options.no_reset = True
    options.app_package = 'com.example.flutter_application_1'
    options.app_activity = 'com.example.flutter_application_1.MainActivity'
    
    start = time.time()
    try:
        driver = webdriver.Remote("http://localhost:4723", options=options)
        print(f"Connected in {time.time() - start:.2f}s")
        print(f"Current package: {driver.current_package}")
        driver.quit()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_connection()
