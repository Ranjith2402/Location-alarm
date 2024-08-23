class CommonClass(BaseException):
    def __init__(self, short_error=''):
        self.short_error = short_error


class SaveFailedException(CommonClass, PermissionError):
    def __init__(self, *args, short_error=''):
        super().__init__(short_error=short_error)
        super(CommonClass, self).__init__(*args)


if __name__ == '__main__':
    try:
        raise SaveFailedException(short_error='Some error')
        # raise PermissionError
    except SaveFailedException as e:
        print('SaveFailed')
        print(e.short_error)
    except PermissionError:
        print('PermissionError')
