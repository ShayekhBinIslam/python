class ProtocolError(Exception):
    pass

class ExecutionError(Exception):
    pass

class StorageError(Exception):
    pass

class SchemaError(Exception):
    pass

class ProtocolRejectedError(ProtocolError):
    def __init__(self, message : str = ''):
        super().__init__(message or 'Protocol rejected')
    pass

class ProtocolNotFoundError(ProtocolError):
    pass

class ProtocolRetrievalError(ProtocolError):
    pass

class ProtocolTransportError(ProtocolError):
    pass
