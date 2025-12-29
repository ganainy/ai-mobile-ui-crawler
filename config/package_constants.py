"""
Package name constants for Android system and third-party applications.

All package names can be overridden via environment variables with sensible defaults.
This provides flexibility for different Android versions and device manufacturers.
"""

from typing import List


class PackageConstants:
    """Centralized package name configuration."""
    
    # PCAPdroid package for traffic capture
    PCAPDROID_PACKAGE = "com.emanuelef.remote_capture"
    
    # System UI package (essential for navigation)
    SYSTEM_UI_PACKAGE = "com.android.systemui"
    
    # Default allowed external packages (can be extended via config)
    # Only permission controller by default - app package is handled dynamically
    DEFAULT_ALLOWED_EXTERNAL_PACKAGES = [
        "com.google.android.permissioncontroller",
    ]
    
    # System package prefixes (used to identify system packages)
    SYSTEM_PACKAGE_PREFIXES = [
        "android.",
        "com.android.",
        "com.google.android.",
        "com.qualcomm.",
        "com.qti.",
        "com.miui.",
        "com.xiaomi.",
        "vendor.",
        "org.ifaa.",
        "de.qualcomm.",
        "com.sec.",
        "com.samsung.",
        "com.huawei.",
    ]
    
    # Known browser packages - when detected, auto-back instead of crawling
    # This handles external links that open in browsers
    BROWSER_PACKAGES = [
        "com.android.chrome",
        "com.brave.browser",
        "org.mozilla.firefox",
        "com.opera.browser",
        "com.opera.mini.native",
        "com.microsoft.emmx",  # Edge
        "com.sec.android.app.sbrowser",  # Samsung Browser
        "com.duckduckgo.mobile.android",
        "com.UCMobile.intl",  # UC Browser
        "com.vivaldi.browser",
        "org.chromium.chrome",
        "com.kiwibrowser.browser",
    ]
    
    @classmethod
    def get_allowed_external_packages(cls, additional: List[str] = None) -> List[str]:
        """Get allowed external packages with optional additional packages."""
        packages = cls.DEFAULT_ALLOWED_EXTERNAL_PACKAGES.copy()
        if additional:
            packages.extend(additional)
        return list(set(packages))  # Remove duplicates
    
    @classmethod
    def is_system_package(cls, package_name: str) -> bool:
        """Check if a package name matches system package prefixes."""
        return any(package_name.startswith(prefix) for prefix in cls.SYSTEM_PACKAGE_PREFIXES)
    
    @classmethod
    def is_browser_package(cls, package_name: str) -> bool:
        """Check if a package is a known browser (for external link detection)."""
        return package_name in cls.BROWSER_PACKAGES
