from abc import ABC, abstractmethod

class SenderTransporter(ABC):
    @abstractmethod
    def send_query(self, query, target):
        pass

class HTTPSenderTransporter(SenderTransporter):
    def send_query(self, query, target):
        pass