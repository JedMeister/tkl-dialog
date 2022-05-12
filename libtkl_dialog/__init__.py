# Copyright (c) 2022 TurnKey GNU/Linux <admin@turnkeylinux.org>

import re
import os
import sys
import logging
import subprocess
from subprocess import PIPE, STDOUT
from tempfile import mkstemp
from typing import Union

import dialog

from .utils import password_complexity

# minimum passw length
PASS_LENGTH = 8
# passw complexity (how many of upper, lower, num & symbols)
PASS_COMPLEXITY = 3
# complexity requirement length limit (i.e. override complexity if this long)
COMPLEXITY_LEN_LMT = 28
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


class Dialog:

    PASS_LENGTH = PASS_LENGTH
    PASS_COMPLEXITY = PASS_COMPLEXITY
    COMPLEXITY_LEN_LMT = COMPLEXITY_LEN_LMT

    def __init__(self,
                 title: str,
                 width: int = 60,
                 height: int = 20,
                 ok_label: str = None,
                 cancel_label: str = None,
                 colors: bool = False,
                 mouse: bool = False):
        self.width = width
        self.height = height

        self.console = dialog.Dialog(dialog="dialog")
        self.console.set_background_title(title)
        self.console.add_persistent_args(["--no-collapse"])
        if ok_label:
            self.console.add_persistent_args(["--ok-label", ok_label])
        if cancel_label:
            self.console.add_persistent_args(["--cancel-label", cancel_label])
        if colors:
            self.console.add_persistent_args(["--colors"])
        if not mouse:
            self.console.add_persistent_args(["--no-mouse"])

    def _handle_exitcode(self, retcode: str) -> bool:
        logging.debug(f"_handle_exitcode(retcode={retcode!r})")
        if retcode == self.console.ESC:  # ESC, ALT+?
            text = "Do you really want to quit?"
            if self.console.yesno(text) == self.console.OK:
                sys.exit(0)
            return False

        logging.debug(
                "_handle_exitcode(): [no conditions met, returning True]")
        return True

    def _calc_height(self, text: str) -> int:
        height = 6
        for line in text.splitlines():
            height += (len(line) // self.width) + 1
        return height

    def wrapper(self, dialog_name: str, text: str, *args, **kws
                ) -> list[str]:
        logging.debug(
            f"wrapper(dialog_name={dialog_name!r}, text=<redacted>,"
            f" *{args!r}, **{kws!r})")
        try:
            method = getattr(self.console, dialog_name)
        except AttributeError as e:
            logging.error(
                f"wrapper(dialog_name={dialog_name!r}, ...) raised exception",
                exc_info=e)
            raise TklDialogError("dialog not supported: " + dialog_name)

        while 1:
            #try:
                retcode = method("\n" + text, *args, **kws)
                logging.debug(
                    f"wrapper(dialog_name={dialog_name!r}, ...) ->"
                    f" {retcode!r}")

                if self._handle_exitcode(retcode):
                    break

            #except Exception as e:
            #    raise
            #    sio = StringIO()
            #    traceback.print_exc(file=sio)
            #    logging.error(
            #        f"wrapper(dialog_name={dialog_name!r}) raised exception",
            #        exc_info=e)
            #    self.msgbox("Caught exception", sio.getvalue())
        if type(retcode) == str:
            return [retcode]
        return retcode

    def error(self, text: str) -> str:
        height = self._calc_height(text)
        return self.wrapper(
                "msgbox", text, height, self.width, title="Error")[0]

    def msgbox(self, title: str, text: str, button_label: str = None) -> str:
        height = self._calc_height(text)
        kwargs = {'title': title}
        if button_label:
            kwargs['button_label'] = button_label
        logging.debug(f"msgbox(title={title!r}, text=<redacted>)")
        return self.wrapper("msgbox", text, height, self.width, **kwargs)[0]

    def infobox(self, text: str) -> str:
        height = self._calc_height(text)
        logging.debug(f"infobox(text={text!r}")
        return self.wrapper("infobox", text, height, self.width)[0]

    def inputbox(self,
                 title: str,
                 text: str,
                 init: str = '',
                 ok_label: str = None,
                 cancel_label: str = None
                 ) -> list[str]:
        logging.debug(
                f"inputbox(title={title!r}, text=<redacted>,"
                f" init={init!r}, ok_label={ok_label!r},"
                f" cancel_label={cancel_label!r})")

        height = self._calc_height(text) + 3
        kwargs = {'title': title, 'init': init}
        if ok_label:
            kwargs['ok_label'] = ok_label
        if cancel_label:
            kwargs['cancel_label'] = cancel_label
        if cancel_label == "":
            kwargs['no_cancel'] = 'True'
        logging.debug(f"inputbox(...) [calculated height={height},"
                      f" no_cancel={kwargs['no_cancel']}")
        return self.wrapper("inputbox", text, height, self.width, **kwargs)

    def yesno(self,
              title: str,
              text: str,
              yes_label: str = None,
              no_label: str = None
              ) -> bool:
        height = self._calc_height(text)
        kwargs = {'title':title}
        if yes_label:
            kwargs['yes_label'] = yes_label
        if no_label:
            kwargs['no_label'] = no_label
        retcode = self.wrapper("yesno", text, height, self.width, **kwargs)
        logging.debug(
                f"yesno(title={title!r}, text=<redacted>,"
                f" yes_label={yes_label!r}, no_label={no_label!r})"
                f" -> {retcode}")
        return True if retcode == 'ok' else False

    def menu(self,
             title: str,
             text: str,
             choices: list[tuple[str]],
             no_cancel: bool = False
             ) -> str:
        """choices: array of tuples
            [ (opt1, opt1_text), (opt2, opt2_text) ]
        """
        kwargs = {'title': title, 'menu_height': len(choices) + 1,
                  'choices': choices}
        if no_cancel:
            kwargs['no_cancel'] = no_cancel
        retcode, choice = self.wrapper("menu", text, self.height, self.width,
                                       **kwargs)
        return choice

    def get_passw(self,
                     title: str,
                     text: str,
                     pass_len: int = None,
                     min_complexity: int = None,
                     complexity_len_lmt: int = None,
                     blacklist: list[str] = []
                     ) -> str:
        if not pass_len:
            pass_len = PASS_LENGTH
        if not min_complexity:
            min_complexity = PASS_COMPLEXITY
        if not complexity_len_lmt and complexity_len_lmt != 0:
            complexity_len_lmt = COMPLEXITY_LEN_LMT
        req_string = (
            f'\n\nPassword Requirements\n - must be at least {pass_len}'
            f' characters long\n - must contain characters from at'
            f' least {min_complexity} of the following categories: uppercase,'
            f' lowercase, numbers, symbols\n')
        if complexity_len_lmt > pass_len:
            req_string = (
                f'{req_string}\n   (override complexity overridden if longer'
                f' than {complexity_len_lmt})')
        if blacklist:
            blist = ', '.join(f'"{item}"' for item in blacklist)
            req_string = (
                f'{req_string}\n - must NOT contain these chars: {blist}')
        height = self._calc_height(text+req_string) + 3

        def ask(title, text: str) -> str:
            text = f'text\nreq_string'
            return self.wrapper(
                    'passwbox', text, height, self.width, title=title,
                    ok_label='OK', no_cancel='True', insecure=True)[1]

        while 1:
            passw = ask(title, text)
            if not passw:
                self.error("Please enter non-empty passw!")
                continue

            if isinstance(pass_len, int):
                if len(passw) < pass_len:
                    self.error(
                        f"Password must be at least {pass_len} characters.")
                continue
            if complexity_len_lmt != 0 or len(passw) <= complexity_len_lmt:
                if password_complexity(passw) < min_complexity:
                    if min_complexity <= 3:
                        self.error(
                            "Insecure passw! Mix uppercase, lowercase,"
                            " and at least one number. Multiple words and"
                            " punctuation are highly recommended but not"
                            " strictly required.")
                    elif min_complexity == 4:
                        self.error(
                            "Insecure passw! Mix uppercase, lowercase,"
                            " numbers and at least one special/punctuation"
                            " character. Multiple words are highly"
                            " recommended but not strictly required.")
                continue

            found_items = []
            for item in blacklist:
                if item in passw:
                    found_items.append(item)
            if found_items:
                self.error(f'Password can NOT include these characters:'
                           f' {blacklist}. Found {found_items}')
                continue

            if passw == ask(title, 'Confirm password'):
                return passw

            self.error('Password mismatch, please try again.')

    def get_email(self, title: str, text: str, init: str = '') -> str:
        logging.debug(
                f'get_email(title={title!r}, text=<redacted>, init={init!r})')
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

    def run_cmd(self, cmd: list[str], cmd_txt: str = None
                ) -> tuple[int, list[str]]:
        if not cmd_txt:
            cmd_text = ' '.join(cmd)
        tmp_fd, tmp_file = mkstemp()
        p = subprocess.Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True)
        t = subprocess.Popen(['tee', tmp_file], stdin=p.stdout,
                              stdout=PIPE, stderr=STDOUT, text=True)
        if t.stdout:
            d = self.console.progressbox(fd=t.stdout.fileno(),
                                         text=f"Running '{cmd_txt}':")
        if not p.returncode:
            p.wait()
        with open(tmp_file, 'r') as fob:
            output = fob.readlines()
        os.remove(tmp_file)
        return (p.returncode, output)
