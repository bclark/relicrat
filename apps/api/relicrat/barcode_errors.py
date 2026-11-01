"""Safe adapter failures shared by installed barcode providers."""
class LookupUnavailable(Exception):
    pass


class LookupTimeout(LookupUnavailable):
    pass


class LookupBusy(Exception):
    pass
