from python_package_template.__main__ import main


def test_main_prints_version(capsys):
    """Test that main prints the package name and version."""
    main()
    captured = capsys.readouterr()
    assert captured.out.startswith('python_package_template ')
    assert len(captured.out.strip()) > len('python_package_template ')
