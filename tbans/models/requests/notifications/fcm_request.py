from tbans.models.requests.notifications.notification_request import NotificationRequest


class FCMRequest(NotificationRequest):
    """ Represents a notification payload and a delivery option to send to FCM.

    https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages

    Attributes:
        notification (Notification): The Notification to send.
        token (string): The FCM registration token to send a message to.
        topic (string): The FCM topic name to send a message to.
        condition (string): The topic condition to send a message.
    """

    def __init__(self, notification, token=None, topic=None, condition=None):
        """
        Note:
            Should only supply one delivery method - either token, topic, or connection.

        Args:
            notification (Notification): The Notification to send.
            token (string): The FCM registration token to send a message to.
            topic (string): The FCM topic name to send a message to.
            condition (string): The topic condition to send a message.
        """
        super(FCMRequest, self).__init__(notification)

        # Ensure we've only passed one delivery option
        delivery_options = [x for x in [token, topic, condition] if x is not None]
        if len(delivery_options) == 0:
            raise TypeError('FCMRequest requires a delivery option - token, topic, or condition')
        elif len(delivery_options) > 1:
            raise TypeError('FCMRequest only accepts one delivery option - token, topic, or condition')

        # Ensure our delivery option looks right
        if not isinstance(delivery_options[0], basestring):
            raise ValueError('FCMRequest delivery option must be a string')

        self.token = token
        self.topic = topic
        self.condition = condition

    def __str__(self):
        deliver_option = self._delivery_option()
        return 'FCMRequest({}="{}", notification={})'.format(deliver_option[0], deliver_option[1], str(self.notification))

    def json_string(self):
        """ JSON string representation of an FCMRequest object.

        JSON for FCMRequest will look like...
        {
            'message': {
                "data": {...},
                "notification": {...},
                "android": {...},
                "webpush": {...},
                "apns": {...},

                // Union field target can be only one of the following:
                "token": string,
                "topic": string,
                "condition": string
                // End of list of possible types for union field target.
            }
        }

        Fields that are not passed (ex - superfluous delivery options) will be excluded.

        Returns:
            string: JSON representation of the FCMRequest.
        """
        json_dict = {}

        # Setup our delivery option
        delivery_option = self._delivery_option()
        json_dict[delivery_option[0]] = delivery_option[1]

        # One of data or notification payload should be not-None, or both
        data_payload = self.notification.data_payload if self.notification.data_payload else {}
        # Add notification type to data payload
        from consts.notification_type import NotificationType
        data_payload['message_type'] = NotificationType.type_names[type(self.notification)._type()]
        json_dict['data'] = data_payload

        FCMRequest._set_payload(json_dict, 'notification', self.notification.notification_payload)

        from tbans.consts.platform_payload_type import PlatformPayloadType
        FCMRequest._set_platform_payload(json_dict, PlatformPayloadType.ANDROID, self.notification.android_payload, self.notification.platform_payload)
        FCMRequest._set_platform_payload(json_dict, PlatformPayloadType.APNS, self.notification.apns_payload, self.notification.platform_payload)
        FCMRequest._set_platform_payload(json_dict, PlatformPayloadType.WEBPUSH, self.notification.webpush_payload, self.notification.platform_payload)

        import json
        return json.dumps({'message': json_dict})

    def send(self):
        """ Attempt to send FCMRequest.

        Return:
            NotificationResponse: content/status_code
        """
        from google.appengine.api import urlfetch
        from tbans.models.requests.notifications.notification_response import NotificationResponse
        from tbans.utils.auth_utils import get_firebase_messaging_access_token

        # Build the request
        headers = {
            'Authorization': 'Bearer ' + get_firebase_messaging_access_token(),
            'Content-Type': 'application/json'
        }
        message_json = self.json_string()

        try:
            response = urlfetch.fetch(
                url=self._fcm_url,
                payload=message_json,
                method=urlfetch.POST,
                headers=headers
            )
            return FCMRequest._transform_fcm_response(response)
        except Exception, e:
            # https://cloud.google.com/appengine/docs/standard/python/refdocs/google.appengine.api.urlfetch_errors
            return NotificationResponse(500, str(e))

    @property
    def _fcm_url(self):
        from google.appengine.api.app_identity import app_identity
        app_id = app_identity.get_application_id()
        return 'https://fcm.googleapis.com/v1/projects/{}/messages:send'.format(app_id)

    def _delivery_option(self):
        """ Returns a tuple (type_string, value) for the FCMRequest delivery option. """
        if self.token:
            return ('token', self.token)
        elif self.topic:
            return ('topic', self.topic)
        elif self.condition:
            return ('condition', self.condition)

    @staticmethod
    def _set_payload(json_dict, key, platform_payload):
        """ Set a platform_payload.payload_dict for the given key, if it's not None. """
        if platform_payload:
            payload_dict = platform_payload.payload_dict
            if payload_dict:
                json_dict[key] = payload_dict

    @staticmethod
    def _set_platform_payload(json_dict, platform_type, platform_payload, default_platform_payload):
        """
        Default to using the default_platform_payload, if we have one.
        Use platform_payload (platform-specific payload override) if not-None.
        """
        from tbans.consts.platform_payload_type import PlatformPayloadType
        key = PlatformPayloadType.key_names.get(platform_type, None)
        if key is None:
            return

        if platform_payload:
            FCMRequest._set_payload(json_dict, key, platform_payload)
        elif default_platform_payload:
            default_platform_payload_dict = default_platform_payload.platform_payload_dict(platform_type)
            if default_platform_payload_dict:
                json_dict[key] = default_platform_payload_dict

    @staticmethod
    def _transform_fcm_response(response):
        """ Transforms a HTTP response from FCM -> a NotificationResponse, adding error information.

        Taken from https://github.com/firebase/firebase-admin-python/blob/932cf17a6f222c627dbd1502658f3eb338077250/firebase_admin/messaging.py

        Error JSON from FCM will look like...
        {
          "error": {
            "code": 404,
            "message": "Requested entity was not found.",
            "status": "NOT_FOUND",
            "details": [
              {
                "@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                "errorCode": "UNREGISTERED"
              }
            ]
          }
        }

        Success JSON from FCM will look like...
        {
          "name": "projects/{project_id}/messages/1545762214218984"
        }
        """
        from tbans.models.requests.notifications.notification_response import NotificationResponse
        from tbans.utils.json_utils import json_string_to_dict

        data = json_string_to_dict(response.content)

        error_dict = data.get('error', None)
        # If we didn't error - go ahead and return the original response information
        if error_dict is None:
            return NotificationResponse(response.status_code, response.content)

        http_code = error_dict.get('code')

        # Get the FCM error code - we should try to act on this
        error_code = None
        # Pull the FCM v1 new error code
        for detail in error_dict.get('details', []):
            if detail.get('@type') == 'type.googleapis.com/google.firebase.fcm.v1.FcmError':
                error_code = detail.get('errorCode')
                break
        # Fall back to the FCM v1 canonical error code
        if not error_code:
            error_code = error_dict.get('status')

        from tbans.consts.fcm_error import FCMError
        fcm_error_code = FCMError.ERROR_CODES.get(error_code, FCMError.UNKNOWN_ERROR)
        # Note - we lose the `message` field from the response
        return NotificationResponse(http_code, fcm_error_code)

    # TODO: Add Google Analytics logging
    # https://github.com/the-blue-alliance/the-blue-alliance/blob/master/notifications/base_notification.py#L141
