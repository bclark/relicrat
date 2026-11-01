"""Safe adapter failures shared by installed barcode providers."""
class LookupUnavailable(Exception):
    pass


class LookupTimeout(LookupUnavailable):
    pass


class LookupBusy(Exception):
    def __init__(self, *args, retry_after=1):
        super().__init__(*args)
        self.retry_after = max(1, min(86400, int(retry_after)))
