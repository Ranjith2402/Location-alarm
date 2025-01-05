import os
import time
from typing import Callable

from custom_errors import CommonClass as CustomError

strf_time_format = '%d-%b-%Y at %I-%M-%S%p %z'  # do not use ':' it raises OSError for creating file


class ErrorHandler:
    def __init__(self, log_directory: str):
        self.log_dir: str = log_directory

    def write_log(self, error_msg: str):
        # todo: this may break, use os.path.join
        file_name = f"{self.log_dir}Error.txt"
        old = ''
        try:
            with open(file_name, 'r') as file:
                old = file.read()
                old += '\n\n' + 'ENDS'.center(80, '-') + '\n\n'
        except FileNotFoundError:
            pass
        with open(file_name, 'w+') as file:
            file.write(old + time.strftime(strf_time_format) + '\n' + error_msg)

    def list_log_files(self, raise_folder_not_found=False) -> list:
        """
        Returns items present in the 'Error log' folder.
        FileNotFoundError is useful when three different types of output are needed.
        That is Files not found, files found and folder not found
        :param raise_folder_not_found: Raise FileNotFoundError if set True
        :raise FileNotFoundError
        :return: List of items in the Error log folder
        """
        try:
            return os.listdir(self.log_dir)
        except FileNotFoundError:
            if raise_folder_not_found:
                raise
            else:
                return []

    def read_error_log(self, target_file: str) -> str:
        # TODO: Multiple files won't created in this version
        try:
            with open(os.path.join(self.log_dir, target_file), 'r') as file:
                return file.read()
        except FileNotFoundError:
            file.close()
            return ''

    def delete_error_log(self, target_file: str):
        try:
            os.remove(self.log_dir + target_file)
        except FileNotFoundError:
            pass

    def call__catch_and_crash(self, func: Callable, *args, raise_error: bool = False, **kwargs):
        def safe_log_writer(txt: str = None):
            if txt is None:
                import traceback
                txt = traceback.format_exc()
            try:
                self.write_log(txt)
            except PermissionError:
                pass
        try:
            out = func(*args, **kwargs)
            return out
        except KeyboardInterrupt:
            pass
        except CustomError as e:
            if e.is_write_log:
                safe_log_writer()
        except SystemExit as e:
            print(e.code)
            if e.code:
                safe_log_writer()
                if raise_error:
                    raise
        except Exception as e:
            print(e.args)
            safe_log_writer()
            if raise_error:
                raise

    def call_wrapper(self, func):
        def wrapper(*args, raise_error, **kwargs):
            self.call__catch_and_crash(func, *args, raise_error=raise_error, **kwargs)
        return wrapper
