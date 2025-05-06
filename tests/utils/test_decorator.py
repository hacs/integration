"""Test HACS decorators."""
import pytest

from custom_components.hacs.utils.decorator import return_none_on_exception


def test_sync_function_no_exception():
    """Test that a synchronous function returning a value works normally."""
    @return_none_on_exception
    def test_func():
        return "test_value"

    assert test_func() == "test_value"


def test_sync_function_with_exception():
    """Test that a synchronous function raising an exception returns None."""
    @return_none_on_exception
    def test_func():
        raise ValueError("Test exception")

    assert test_func() is None


def test_sync_method_no_exception():
    """Test that a synchronous method returning a value works normally."""
    class TestClass:
        @return_none_on_exception
        def test_method(self):
            return "test_value"

    instance = TestClass()
    assert instance.test_method() == "test_value"


def test_sync_method_with_exception():
    """Test that a synchronous method raising an exception returns None."""
    class TestClass:
        @return_none_on_exception
        def test_method(self):
            raise ValueError("Test exception")

    instance = TestClass()
    assert instance.test_method() is None


@pytest.mark.asyncio
async def test_async_function_no_exception():
    """Test that an async function returning a value works normally."""
    @return_none_on_exception
    async def test_func():
        return "test_value"

    assert await test_func() == "test_value"


@pytest.mark.asyncio
async def test_async_function_with_exception():
    """Test that an async function raising an exception returns None."""
    @return_none_on_exception
    async def test_func():
        raise ValueError("Test exception")

    assert await test_func() is None


@pytest.mark.asyncio
async def test_async_method_no_exception():
    """Test that an async method returning a value works normally."""
    class TestClass:
        @return_none_on_exception
        async def test_method(self):
            return "test_value"

    instance = TestClass()
    assert await instance.test_method() == "test_value"


@pytest.mark.asyncio
async def test_async_method_with_exception():
    """Test that an async method raising an exception returns None."""
    class TestClass:
        @return_none_on_exception
        async def test_method(self):
            raise ValueError("Test exception")

    instance = TestClass()
    assert await instance.test_method() is None


@pytest.mark.asyncio
async def test_async_method_with_args():
    """Test that an async method with arguments works normally."""
    class TestClass:
        @return_none_on_exception
        async def test_method(self, arg1, arg2=None):
            if arg2 is None:
                return arg1
            return f"{arg1}_{arg2}"

    instance = TestClass()
    assert await instance.test_method("test") == "test"
    assert await instance.test_method("test", "value") == "test_value"


@pytest.mark.asyncio
async def test_async_method_with_args_exception():
    """Test that an async method with arguments that raises an exception returns None."""
    class TestClass:
        @return_none_on_exception
        async def test_method(self, arg1, arg2=None):
            if arg2 is None:
                raise ValueError("Test exception")
            return f"{arg1}_{arg2}"

    instance = TestClass()
    assert await instance.test_method("test") is None
    assert await instance.test_method("test", "value") == "test_value"
