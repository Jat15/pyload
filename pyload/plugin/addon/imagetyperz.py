# -*- coding: utf-8 -*-
#@author: mkaay, RaNaN, zoidberg

from __future__ import with_statement
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from _thread import start_new_thread
from pycurl import FORM_FILE, LOW_SPEED_TIME
import re
from base64 import b64encode

from pyload.network.requestfactory import get_url, get_request
from pyload.plugin.hook import Hook


class ImageTyperzException(Exception):
    def __init__(self, err):
        self.err = err

    def get_code(self):
        return self.err

    def __str__(self):
        return "<ImageTyperzException %s>" % self.err

    def __repr__(self):
        return "<ImageTyperzException %s>" % self.err


class ImageTyperz(Hook):
    __name__ = "ImageTyperz"
    __version__ = "0.04"
    __description__ = """Send captchas to ImageTyperz.com"""
    __config__ = [("activated", "bool", "Activated", False),
                  ("username", "str", "Username", ""),
                  ("passkey", "password", "Password", ""),
                  ("force", "bool", "Force IT even if client is connected", False)]
    __author_name__ = ("RaNaN", "zoidberg")
    __author_mail__ = ("Mast3rRaNaN@hotmail.de", "zoidberg@mujmail.cz")

    SUBMIT_URL = "http://captchatypers.com/Forms/UploadFileAndGetTextNEW.ashx"
    RESPOND_URL = "http://captchatypers.com/Forms/SetBadImage.ashx"
    GETCREDITS_URL = "http://captchatypers.com/Forms/RequestBalance.ashx"

    def setup(self):
        self.info = {}

    def get_credits(self):
        response = get_url(self.GETCREDITS_URL, post={"action": "REQUESTBALANCE", "username": self.get_config("username"),
                                                     "password": self.get_config("passkey")})

        if response.startswith('ERROR'):
            raise ImageTyperzException(response)

        try:
            balance = float(response)
        except Exception:
            raise ImageTyperzException("invalid response")

        self.log_info("Account balance: $%s left" % response)
        return balance

    def submit(self, captcha, captchaType="file", match=None):
        req = get_request()
        #raise timeout threshold
        req.c.setopt(LOW_SPEED_TIME, 80)

        try:
            #workaround multipart-post bug in HTTPRequest.py
            if re.match("^[A-Za-z0-9]*$", self.get_config("passkey")):
                multipart = True
                data = (FORM_FILE, captcha)
            else:
                multipart = False
                with open(captcha, 'rb') as f:
                    data = f.read()
                data = b64encode(data)

            response = req.load(self.SUBMIT_URL, post={"action": "UPLOADCAPTCHA",
                                                       "username": self.get_config("username"),
                                                       "password": self.get_config("passkey"), "file": data},
                                                       multipart=multipart)
        finally:
            req.close()

        if response.startswith("ERROR"):
            raise ImageTyperzException(response)
        else:
            data = response.split('|')
            if len(data) == 2:
                ticket, result = data
            else:
                raise ImageTyperzException("Unknown response %s" % response)

        return ticket, result

    def new_captcha_task(self, task):
        if "service" in task.data:
            return False

        if not task.isTextual():
            return False

        if not self.get_config("username") or not self.get_config("passkey"):
            return False

        if self.pyload.is_client_connected() and not self.get_config("force"):
            return False

        if self.get_credits() > 0:
            task.handler.append(self)
            task.data['service'] = self.__name__
            task.setWaiting(100)
            start_new_thread(self.processCaptcha, (task,))

        else:
            self.log_info("Your %s account has not enough credits" % self.__name__)

    def captcha_invalid(self, task):
        if task.data['service'] == self.__name__ and "ticket" in task.data:
            response = get_url(self.RESPOND_URL, post={"action": "SETBADIMAGE", "username": self.get_config("username"),
                                                      "password": self.get_config("passkey"),
                                                      "imageid": task.data["ticket"]})

            if response == "SUCCESS":
                self.log_info("Bad captcha solution received, requested refund")
            else:
                self.log_error("Bad captcha solution received, refund request failed", response)

    def process_captcha(self, task):
        c = task.captchaFile
        try:
            ticket, result = self.submit(c)
        except ImageTyperzException as e:
            task.error = e.getCode()
            return

        task.data["ticket"] = ticket
        task.setResult(result)
