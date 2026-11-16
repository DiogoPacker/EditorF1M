import pytest

from backend.application.services import display_name


@pytest.mark.parametrize(("encoded", "expected"), [
    ("[STRING_LITERAL:Value=|Rafael|]", "Rafael"),
    ("[STRING_LITERAL:Value=|Câmara|]", "Câmara"),
    ("[STRING_LITERAL:Value=|CAM|]", "CAM"),
    ("[STRING_LITERAL:Value=|Juan Manuel|]", "Juan Manuel"),
    ("[STRING_LITERAL:Value=|da Câmara|]", "da Câmara"),
    ("[StaffName_Forename_Male_Lewis]", "Lewis"),
    ("[DriverCode_Ham]", "Ham"),
    ("Rafael", "Rafael"),
])
def test_names_and_driver_codes(encoded, expected):
    assert display_name(encoded) == expected
