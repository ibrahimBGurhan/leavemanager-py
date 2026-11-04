# Is kurali ihlalleri (docs/conventions.md, Error handling). Turkce mesaji web kurar;
# burada yalniz ihlalin turu ve verisi tasinir.


class LeaveRequestError(Exception):
    pass


class EmployeeNotFound(LeaveRequestError):
    def __init__(self, employee_id):
        super().__init__(employee_id)
        self.employee_id = employee_id


class InvalidDateRange(LeaveRequestError):
    def __init__(self, start, end):
        super().__init__(start, end)
        self.start = start
        self.end = end


class InsufficientBalance(LeaveRequestError):
    def __init__(self, remaining, requested):
        super().__init__(remaining, requested)
        self.remaining = remaining
        self.requested = requested
