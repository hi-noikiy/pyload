# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
import time
import traceback

from module.plugins.internal.Plugin import Plugin


class Captcha(Plugin):
    __name__    = "Captcha"
    __type__    = "captcha"
    __version__ = "0.37"
    __status__  = "testing"

    __description__ = """Base anti-captcha plugin"""
    __license__     = "GPLv3"
    __authors__     = [("Walter Purcaro", "vuolter@gmail.com")]


    def __init__(self, plugin):  #@TODO: Pass pyfile instead plugin, so store plugin's html in its associated pyfile as data
        self.pyload = plugin.pyload
        self.plugin = plugin
        self.info   = {}  #: Provide information in dict here
        self.task   = None  #: captchaManager task

        self.init()


    def init(self):
        """
        Initialize additional data structures
        """
        pass


    def _log(self, level, plugintype, pluginname, messages):
        return self.plugin._log(level,
                                plugintype,
                                "%s: %s" % (self.plugin.__name__, self.__name__),
                                messages)


    def recognize(self, image):
        """
        Extend to build your custom anti-captcha ocr
        """
        pass


    def decrypt(self, url, get={}, post={}, ref=False, cookies=False, decode=False,
                input_type='jpg', output_type='textual', ocr=True, timeout=120):
        img = self.load(url, get=get, post=post, ref=ref, cookies=cookies, decode=decode)
        return self._decrypt(img, input_type, output_type, ocr, timeout)


    #@TODO: Definitely choose a better name for this method!
    def _decrypt(self, raw, input_type='jpg', output_type='textual', ocr=None, timeout=120):
        """
        Loads a captcha and decrypts it with ocr, plugin, user input

        :param raw: image raw data
        :param get: get part for request
        :param post: post part for request
        :param cookies: True if cookies should be enabled
        :param input_type: Type of the Image
        :param output_type: 'textual' if text is written on the captcha\
        or 'positional' for captcha where the user have to click\
        on a specific region on the captcha
        :param ocr: if True, ocr is not used

        :return: result of decrypting
        """
        time_ref = ("%.2f" % time.time())[-6:].replace(".", "")

        with open(os.path.join("tmp", "captcha_image_%s_%s.%s" % (self.plugin.__name__, time_ref, input_type)), "wb") as tmp_img:
            tmp_img.write(raw)

            if ocr is not False:
                if isinstance(ocr, basestring):
                    OCR = self.pyload.pluginManager.loadClass("captcha", ocr)  #: Rename `captcha` to `ocr` in 0.4.10

                    if self.plugin.pyfile.abort:
                        self.plugin.abort()

                    result = OCR(self.plugin).recognize(tmp_img.name)

                else:
                    result = self.recognize(tmp_img.name)

            else:
                captchaManager = self.pyload.captchaManager

                try:
                    self.task = captchaManager.newTask(raw, input_type, tmp_img.name, output_type)
                    captchaManager.handleCaptcha(self.task)
                    self.task.setWaiting(max(timeout, 50))  #@TODO: Move to `CaptchaManager` in 0.4.10

                    while self.task.isWaiting():
                        if self.plugin.pyfile.abort:
                            self.plugin.abort()
                        time.sleep(1)

                finally:
                    captchaManager.removeTask(self.task)

                if self.task.error:
                    self.fail(task.error)

                elif not self.task.result:
                    self.invalid()
                    self.plugin.retry(reason=_("No captcha result obtained in appropiate time"))

                result = self.task.result
                self.log_info(_("Captcha result: ") + result)  #@TODO: Remove from here?

        if not self.pyload.debug:
            try:
                os.remove(tmp_img.name)

            except OSError, e:
                self.log_warning(_("Error removing: %s") % tmp_img.name, e)
                traceback.print_exc()

        return result


    def invalid(self):
        if not self.task:
            return

        self.log_error(_("Invalid captcha"))
        self.task.invalid()


    def correct(self):
        if not self.task:
            return

        self.log_info(_("Correct captcha"))
        self.task.correct()