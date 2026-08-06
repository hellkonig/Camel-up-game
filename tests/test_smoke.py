from camel_up.cli.main import main


def test_cli_entry_point_is_importable() -> None:
    assert callable(main)
