"""Unit tests for common exceptions."""

import pytest

from app.src.common.exceptions import BusinessLogicError, ValidationError, NotFoundError


class TestCommonExceptions:
    """Test cases for common exception classes."""

    def test_business_logic_error_creation(self):
        """Test BusinessLogicError creation."""
        message = "Invalid business rule"
        error = BusinessLogicError(message)

        assert str(error) == message
        assert error.message == message
        assert isinstance(error, Exception)

    def test_validation_error_creation(self):
        """Test ValidationError creation."""
        message = "Invalid input data"
        error = ValidationError(message)

        assert str(error) == message
        assert error.message == message
        assert isinstance(error, Exception)

    def test_not_found_error_creation(self):
        """Test NotFoundError creation."""
        message = "Resource not found"
        error = NotFoundError(message)

        assert str(error) == message
        assert error.message == message
        assert isinstance(error, Exception)

    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from Exception."""
        assert issubclass(BusinessLogicError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(NotFoundError, Exception)

    def test_exception_raising(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(BusinessLogicError) as excinfo:
            raise BusinessLogicError("Test error")

        assert "Test error" in str(excinfo.value)

        with pytest.raises(ValidationError) as excinfo:
            raise ValidationError("Validation failed")

        assert "Validation failed" in str(excinfo.value)

        with pytest.raises(NotFoundError) as excinfo:
            raise NotFoundError("Not found")

        assert "Not found" in str(excinfo.value)