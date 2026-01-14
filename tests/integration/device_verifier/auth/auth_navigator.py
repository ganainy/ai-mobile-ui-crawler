from .auth_configs import AuthMode

class AuthNavigator:
    """Navigates to auth screens using deep links."""
    
    def __init__(self, deep_link_navigator):
        self.navigator = deep_link_navigator
        self.base_url = "testapp://auth/"
    
    def go_to_signup(self, mode: AuthMode = AuthMode.BASIC) -> bool:
        """
        Navigate to signup screen with specified auth mode.
        """
        url = f"{self.base_url}signup?mode={mode.value}"
        return self.navigator.navigate_to(url)
    
    def go_to_signin(self) -> bool:
        """
        Navigate to sign-in screen.
        """
        return self.navigator.navigate_to(f"{self.base_url}signin")
    
    def trigger_email_verification(self, token: str = "TESTTOKEN") -> bool:
        """
        Trigger email verification deep link.
        """
        return self.navigator.navigate_to(f"{self.base_url}verify?token={token}")
