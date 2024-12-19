

'''Exception for pandas cannot access an important Field that should be there'''
class ColumnsNotFound(Exception):
     def __init__(self, message):
        self.message = message
        super().__init__(self.message)