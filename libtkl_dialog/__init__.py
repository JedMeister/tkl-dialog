# Copyright (c) 2022 TurnKey GNU/Linux <admin@turnkeylinux.org>

import re
import os
import sys
import dialog
import logging
from typing import Union

EMAIL_RE = re.compile(r"(?:^|\s).*\S@\S+(?:\s|$)", re.IGNORECASE)

LOG_LEVEL = logging.INFO
if 'DIALOG_DEBUG' in os.environ.keys():
    LOG_LEVEL = logging.DEBUG

logging.basicConfig(
    filename='/var/log/dialog.log',
    encoding='utf-8',
    level=LOG_LEVEL
)


class TklDialogError(Exception):
    pass


def password_complexity(password: str) -> Union[str, int]:
    """return password complexity score from 0 (invalid) to 4 (strong)"""

    lowercase = re.search('[a-z]', password) is not None
    uppercase = re.search('[A-Z]', password) is not None
    number = re.search('\d', password) is not None
    nonalpha = re.search('\W', password) is not None

    return sum([lowercase, uppercase, number, nonalpha])


class Dialog:
    def __init__(self,
                 title: str,
                 width: int = 60,
                 height: int = 20,
                 mouse: bool = False):
        self.width = width
        self.height = height

        self.console = dialog.Dialog(dialog="dialog")
        self.console.set_background_title(title)
        self.console.add_persistent_args(["--no-collapse"])
        if not mouse:
            self.console.add_persistent_args(["--no-mouse"])

    def _handle_exitcode(self, retcode: int) -> bool:
        logging.debug(f"_handle_exitcode(retcode={retcode!r})")
        if retcode == self.console.ESC:  # ESC, ALT+?
            text = "Do you really want to quit?"
            if self.console.yesno(text) == self.console.OK:
                sys.exit(0)
            return False

        logging.debug("_handle_exitcode(): [no conditions met, returning True]")
        return True

    def _calc_height(self, text: str) -> int:
        height = 6
        for line in text.splitlines():
            height += (len(line) // self.width) + 1
        return height

    def wrapper(self, dialog_name: str, text: str, *args, **kws) -> int:
        logging.debug(
            f"wrapper(dialog_name={dialog_name!r}, text=<redacted>,"
            +f" *{args!r}, **{kws!r})")
        try:
            method = getattr(self.console, dialog_name)
        except AttributeError as e:
            logging.error(
                    f"wrapper(dialog_name={dialog_name!r}, ...) raised exception",
                    exc_info=e)
            raise TklDialogError("dialog not supported: " + dialog_name)

        while 1:
            try:
                retcode = method("\n" + text, *args, **kws)
                logging.debug(
                    f"wrapper(dialog_name={dialog_name!r}, ...) -> {retcode!r}")

                if self._handle_exitcode(retcode):
                    break

            except Exception as e:
                raise
            #    sio = StringIO()
            #    traceback.print_exc(file=sio)
            #    logging.error(
            #        f"wrapper(dialog_name={dialog_name!r}) raised exception",
            #        exc_info=e)
            #    self.msgbox("Caught exception", sio.getvalue())

        return retcode

    def error(self, text: str) -> int:
        height = self._calc_height(text)
        return self.wrapper("msgbox", text, height, self.width, title="Error")

    def msgbox(self, title: str, text: str) -> int:
        height = self._calc_height(text)
        logging.debug(f"msgbox(title={title!r}, text=<redacted>)")
        return self.wrapper("msgbox", text, height, self.width, title=title)

    def infobox(self, text: str) -> int:
        height = self._calc_height(text)
        logging.debug(f"infobox(text={text!r}")
        return self.wrapper("infobox", text, height, self.width)

    def inputbox(self,
                 title: str,
                 text: str,
                 init: str = '',
                 ok_label: str = "OK",
                 cancel_label: str = "Cancel"
                 ) -> int:
        logging.debug(
                f"inputbox(title={title!r}, text=<redacted>,"
                +f" init={init!r}, ok_label={ok_label!r},"
                +f" cancel_label={cancel_label!r})")

        height = self._calc_height(text) + 3
        no_cancel = True if cancel_label == "" else False
        logging.debug(
                f"inputbox(...) [calculated height={height}, no_cancel={no_cancel}]")
        return self.wrapper("inputbox", text, height, self.width, title=title,
                            init=init, ok_label=ok_label,
                            cancel_label=cancel_label, no_cancel=no_cancel)

    def yesno(self,
              title: str,
              text: str,
              yes_label: str = "Yes",
              no_label: str = "No"
              ) -> bool:
        height = self._calc_height(text)
        retcode = self.wrapper("yesno", text, height, self.width, title=title,
                               yes_label=yes_label, no_label=no_label)
        logging.debug(
                f"yesno(title={title!r}, text=<redacted>,"
                f" yes_label={yes_label!r}, no_label={no_label!r})"
                f" -> {retcode}")
        return True if retcode == 'ok' else False

    def menu(self,
             title: str,
             text: str,
             choices: list[str]
             ) -> str:
        """choices: array of tuples
            [ (opt1, opt1_text), (opt2, opt2_text) ]
        """
        retcode, choice = self.wrapper(
                "menu", text, self.height, self.width,
                menu_height=len(choices)+1, title=title,
                choices=choices, no_cancel=True)
        return choice

    def get_password(self,
                     title: str,
                     text: str,
                     pass_req: int = 8,
                     min_complexity: int = 3,
                     blacklist: list[str] = []
                     ) -> str:
        req_string = (
            f'\n\nPassword Requirements\n - must be at least {pass_req}'
            +' characters long\n - must contain characters from at'
            +f' least {min_complexity} of the following categories: uppercase,'
            +' lowercase, numbers, symbols'
        )
        if blacklist:
            req_string =\
                f'{req_string}. Also must NOT contain these characters: {blacklist}'
        height = self._calc_height(text+req_string) + 3

        def ask(title, text: str) -> int:
            return self.wrapper('passwordbox', text+req_string, height,
                                self.width, title=title, ok_label='OK',
                                no_cancel='True', insecure=True)[1]

        while 1:
            password = ask(title, text)
            if not password:
                self.error("Please enter non-empty password!")
                continue

            if isinstance(pass_req, int):
                if len(password) < pass_req:
                    self.error(f"Password must be at least {pass_req} characters.")
                    continue
            else:
                if not re.match(pass_req, password):
                    self.error("Password does not match complexity"
                               +" requirements.")
                    continue

            if password_complexity(password) < min_complexity:
                if min_complexity <= 3:
                    self.error("Insecure password! Mix uppercase, lowercase,"
                               +" and at least one number. Multiple words and"
                               +" punctuation are highly recommended but not"
                               +" strictly required.")
                elif min_complexity == 4:
                    self.error("Insecure password! Mix uppercase, lowercase,"
                               +" numbers and at least one special/punctuation"
                               +" character. Multiple words are highly"
                               +" recommended but not strictly required.")
                continue

            found_items = []
            for item in blacklist:
                if item in password:
                    found_items.append(item)
            if found_items:
                self.error(
                        f'Password can NOT include these characters: {blacklist}.'
                        +f' Found {found_items}')
                continue

            if password == ask(title, 'Confirm password'):
                return password

            self.error('Password mismatch, please try again.')

    def get_email(self, title: str, text: str, init: str = '') -> str:
        logging.debug(f'get_email(title={title!r}, text=<redacted>, init={init!r})')
        while 1:
            email = self.inputbox(title, text, init, "Apply", "")[1]
            logging.debug(f'get_email(...) email={email!r}')
            if not email:
                self.error('Email is required.')
                continue

            if not EMAIL_RE.match(email):
                self.error('Email is not valid')
                continue

            return email

    def get_input(self, title: str, text: str, init: str = '') -> str:
        while 1:
            s = self.inputbox(title, text, init, "Apply", "")[1]
            if not s:
                self.error(f'{title} is required.')
                continue

            return s
