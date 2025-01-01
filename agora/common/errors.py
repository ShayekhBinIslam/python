class ProtocolError(Exception):
    """Base exception class for protocol-related errors."""

    def __init__(self, message: str = ''):
        """
        Initializes the ProtocolError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class ExecutionError(Exception):
    """Exception raised for errors during the internal execution of routines and toolformers."""

    def __init__(self, message: str = ''):
        """
        Initializes the ExecutionError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class StorageError(Exception):
    """Exception raised for storage-related issues."""

    def __init__(self, message: str = ''):
        """
        Initializes the StorageError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class SchemaError(Exception):
    """Exception raised for schema validation errors."""

    def __init__(self, message: str = ''):
        """
        Initializes the SchemaError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class ProtocolRejectedError(ProtocolError):
    """Exception raised when a protocol is rejected."""

    def __init__(self, message: str = ''):
        """
        Initializes ProtocolRejectedError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to 'Protocol rejected' if empty.
        """
        super().__init__(message or 'Protocol rejected')


class ProtocolNotFoundError(ProtocolError):
    """Exception raised when a protocol is not found."""

    def __init__(self, message: str = ''):
        """
        Initializes ProtocolNotFoundError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class ProtocolRetrievalError(ProtocolError):
    """Exception raised when retrieving a protocol fails."""

    def __init__(self, message: str = ''):
        """
        Initializes ProtocolRetrievalError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)


class ProtocolTransportError(ProtocolError):
    """Exception raised for transport-related protocol errors."""

    def __init__(self, message: str = ''):
        """
        Initializes ProtocolTransportError with an optional message.

        Args:
            message (str, optional): The error message. Defaults to an empty string.
        """
        super().__init__(message)
