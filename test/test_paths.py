from memory.core.paths import slugify


def test_slugify_basic():
    assert slugify("hello world") == "hello_world"


def test_slugify_uppercase():
    assert slugify("DiUngThucAn") == "diungthucan"
    assert slugify("DiUng") == "diung"


def test_slugify_special_chars():
    assert slugify("hello-world!@#") == "hello_world"


def test_slugify_empty():
    assert slugify("") == "topic"


def test_slugify_only_special():
    assert slugify("!@#$%") == "topic"


def test_slugify_underscores():
    assert slugify("di_ung_thuc_an") == "di_ung_thuc_an"


def test_slugify_numbers():
    assert slugify("topic123") == "topic123"
