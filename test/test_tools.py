from glados.tool import all_tools


def test_autoload():
    """Test tools functions is autoloaded."""
    assert len(all_tools) > 0
    assert "roll_dice" in all_tools
    assert "get_weather" in all_tools
