class CommonClass(BaseException):
    def __init__(self, short_error='', is_write_log=False):
        self.short_error = short_error
        self.is_write_log = is_write_log


class SaveFailedException(CommonClass, PermissionError):
    def __init__(self, *args, short_error='', is_write_log=False):
        super().__init__(short_error=short_error, is_write_log=is_write_log)
        super(CommonClass, self).__init__(*args)


class GPSNotImplementedError(CommonClass, NotImplementedError):
    def __init__(self, *args, short_error='', is_write_log=False):
        super().__init__(short_error=short_error, is_write_log=is_write_log)
        super(CommonClass, self).__init__(*args)


class MissingFileError(CommonClass, FileNotFoundError):
    # No idea why I created this ¯\_(ツ)_/¯
    def __init__(self, *args, short_error='', is_write_log=False):
        super().__init__(short_error=short_error, is_write_log=is_write_log)
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
