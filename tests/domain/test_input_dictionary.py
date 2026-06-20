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

    # Test Password
    password_el = {"resourceId": "pwd_widget", "text": "Password", "className": "EditText"}
    assert input_dict.get_suggested_input(password_el) == "Password123!"

    # Test Address
    address_el = {"resourceId": "billing_address", "text": "", "className": "EditText"}
    assert input_dict.get_suggested_input(address_el) == "123 Test St"


def test_input_dictionary_config_overrides():
    config_manager = Mock()
    config_manager.get.side_effect = lambda key, default=None: {
        "test_email": "override@example.com",
        "test_phone": "19999999999",
        "test_username": "custom_user",
        "test_password": "CustomPassword!",
        "test_address": "456 Custom Ave"
    }.get(key, default)

    input_dict = ContextAwareInputDictionary(config_manager=config_manager)

    email_el = {"resourceId": "email_input", "text": ""}
    assert input_dict.get_suggested_input(email_el) == "override@example.com"

    phone_el = {"resourceId": "phone"}
    assert input_dict.get_suggested_input(phone_el) == "19999999999"


def test_input_dictionary_generic_fallback():
    input_dict = ContextAwareInputDictionary(config_manager=None)

    generic_el = {"resourceId": "random_custom_widget_123", "text": "random", "className": "SomeClass"}
    assert input_dict.get_suggested_input(generic_el) == "test input"
