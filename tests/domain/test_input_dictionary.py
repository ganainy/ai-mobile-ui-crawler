from unittest.mock import Mock

from mobile_crawler.domain.input_dictionary import ContextAwareInputDictionary


def test_input_dictionary_default_matching():
    input_dict = ContextAwareInputDictionary(config_manager=None)

    # Test Email
    email_el = {"resourceId": "email_input", "text": "Enter your email", "className": "EditText"}
    assert input_dict.get_suggested_input(email_el) == "test_user@example.com"

    # Test Phone
    phone_el = {"resourceId": "phone_number_field", "text": "", "className": "EditText"}
    assert input_dict.get_suggested_input(phone_el) == "15555555555"

    # Test Address
    address_el = {"resourceId": "billing_address", "text": "", "className": "EditText"}
    assert input_dict.get_suggested_input(address_el) == "123 Test St"


def test_input_dictionary_config_overrides():
    config_manager = Mock()
    config_manager.get.side_effect = lambda key, default=None: {
        "test_address": "456 Custom Ave",
    }.get(key, default)

    input_dict = ContextAwareInputDictionary(
        config_manager=config_manager, email="override@example.com", phone="19999999999"
    )

    email_el = {"resourceId": "email_input", "text": ""}
    assert input_dict.get_suggested_input(email_el) == "override@example.com"

    phone_el = {"resourceId": "phone"}
    assert input_dict.get_suggested_input(phone_el) == "19999999999"


def test_input_dictionary_generic_fallback():
    input_dict = ContextAwareInputDictionary(config_manager=None)

    generic_el = {"resourceId": "random_custom_widget_123", "text": "random", "className": "SomeClass"}
    assert input_dict.get_suggested_input(generic_el) == "test input"


def test_input_dictionary_uses_app_account_for_username_and_password():
    from mobile_crawler.infrastructure.app_account_store import AppAccount

    input_dict = ContextAwareInputDictionary(config_manager=None, app_account=AppAccount("alice", "pw-a"))
    assert input_dict.get_suggested_input({"resourceId": "pwd_widget"}) == "pw-a"
    assert input_dict.get_suggested_input({"resourceId": "login_name"}) == "alice"


def test_input_dictionary_without_app_account_has_no_default_credentials():
    input_dict = ContextAwareInputDictionary(config_manager=None)
    assert input_dict.get_suggested_input({"resourceId": "pwd_widget"}) == ""
    assert input_dict.get_suggested_input({"resourceId": "login_name"}) == ""
