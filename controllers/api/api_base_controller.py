import json
import logging
import urllib
import webapp2

from google.appengine.api import urlfetch
from google.appengine.ext import deferred

from controllers.base_controller import CacheableHandler
from helpers.validation_helper import ValidationHelper
from models.sitevar import Sitevar


# used for deferred call
def track_call(api_action, api_label, x_tba_app_id):
    analytics_id = Sitevar.get_by_id("google_analytics.id")
    if analytics_id is None:
        logging.warning("Missing sitevar: google_analytics.id. Can't track API usage.")
    else:
        GOOGLE_ANALYTICS_ID = analytics_id.contents['GOOGLE_ANALYTICS_ID']
        params = urllib.urlencode({
            'v': 1,
            'tid': GOOGLE_ANALYTICS_ID,
            'cid': '1',
            't': 'event',
            'ec': 'api-v02',
            'ea': api_action,
            'el': api_label,
            'cd1': x_tba_app_id,  # custom dimension 1
            'ni': 1
        })

        analytics_url = 'http://www.google-analytics.com/collect?%s' % params
        urlfetch.fetch(
            url=analytics_url,
            method=urlfetch.GET,
        )


class ApiBaseController(CacheableHandler):

    def __init__(self, *args, **kw):
        super(ApiBaseController, self).__init__(*args, **kw)
        self.response.headers['content-type'] = 'application/json; charset="utf-8"'

    def handle_exception(self, exception, debug):
        """
        Handle an HTTP exception and actually writeout a
        response.
        Called by webapp when abort() is called, stops code excution.
        """
        logging.info(exception)
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
            self.response.out.write(self._errors)
        else:
            self.response.set_status(500)

    def get(self, *args, **kw):
        self._validate_tba_app_id()
        self._errors = ValidationHelper.validate(self._validators)
        if self._errors:
            self.abort(400)

        self._track_call(*args, **kw)
        super(ApiBaseController, self).get(*args, **kw)

    def _track_call_defer(self, api_action, api_label):
        deferred.defer(track_call, api_action, api_label, self.x_tba_app_id)

    def _validate_tba_app_id(self):
        """
        Tests the presence of a X-TBA-App-Id header.
        """
        self.x_tba_app_id = self.request.headers.get("X-TBA-App-Id")
        logging.info("X-TBA-App-ID: {}".format(self.x_tba_app_id))
        if not self.x_tba_app_id:
            self._errors = json.dumps({"Error": "X-TBA-App-Id is a required header."})
            self.abort(400)
        if len(self.x_tba_app_id.split(':')) != 3:
            self._errors = json.dumps({"Error": "X-TBA-App-Id must follow the following format: <team/person id>:<app description>:<version>"})
            self.abort(400)

    def _write_cache_headers(self, seconds):
        if type(seconds) is not int:
            logging.error("Cache-Control max-age is not integer: {}".format(seconds))
            return

        self.response.headers['Cache-Control'] = "public, max-age=%d" % seconds
        self.response.headers['Pragma'] = 'Public'
