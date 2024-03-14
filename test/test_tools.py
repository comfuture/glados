from glados.tool import __registry__, plugin


def test_plugin_decorator():
    @plugin
    def foo(): ...

    assert "foo" in __registry__
    assert __registry__["foo"]["function"] == foo
    assert __registry__["foo"]["meta"] == {}

    @plugin(name="bar", icon="🍺")
    def bar(): ...

    assert "bar" in __registry__
    assert __registry__["bar"]["function"] == bar
    assert __registry__["bar"]["meta"] == {"name": "bar", "icon": "🍺"}


def test_plugin_autoload():
    """Test tools functions is autoloaded."""
    assert len(__registry__) > 0
    assert "get_date" in __registry__
    get_date = __registry__["get_date"]["function"]
    assert hasattr(get_date, "__meta__")
    assert get_date.__meta__.get("name") == "System Date"
    assert get_date.__meta__.get("icon") == "📅"
