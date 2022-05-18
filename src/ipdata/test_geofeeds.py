import pytest

from .geofeeds import Entry, GeofeedValidationError


@pytest.mark.parametrize(
    "entry",
    [
        "172.32.0.0/55,,,,",
        "172.32.0.0/11,,,,",
        "172.32.0.0/11,ZZ,,,",
        "172.32.0.0/11,US,ZZ-ZZ,,",
        "172.32.0.0/11,US,LU-LU,,",
    ],
)
@pytest.mark.geofeed
def test_validation_rules(entry):
    entry = Entry(*entry.split(","))
    with pytest.raises(GeofeedValidationError):
        entry.validate()
