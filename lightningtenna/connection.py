import logging
import time
import threading
import traceback
from hashlib import sha256

import goTenna
from termcolor import colored

import config
import events
import messages
import utilities

logger = logging.getLogger("MESH")

# For SPI connection only, set SPI_CONNECTION to true with proper SPI settings
SPI_CONNECTION = False
SPI_BUS_NO = 0
SPI_CHIP_NO = 0
SPI_REQUEST = 22
SPI_READY = 27


class Connection:
    def __init__(self, name="default", send_to_trio=None, receive_from_trio=None):
        self.api_thread = None
        self.status = {}
        self.in_flight_events = {}
        self._set_frequencies = False
        self._set_tx_power = False
        self._set_bandwidth = False
        self._set_geo_region = False
        self._settings = goTenna.settings.GoTennaSettings(
            rf_settings=goTenna.settings.RFSettings(),
            geo_settings=goTenna.settings.GeoSettings(),
        )
        self._do_encryption = True
        self._awaiting_disconnect_after_fw_update = [False]
        self.gid = (None,)
        self.geo_region = None
        self.events = events.Events(send_to_trio, receive_from_trio)
        self.gateway = 0
        self.handle_message_thread = threading.Thread(
            target=messages.handle_message, args=[self, self.events.msg]
        )
        self.jumbo_thread = threading.Thread()
        self.cli = False
        self.bytes_sent = 0
        self.bytes_received = 0
        self.name = name

    def reset_connection(self):
        if self.api_thread:
            self.api_thread.join()
        self.__init__(self.name)

    @utilities.cli
    def sdk_token(self, sdk_token):
        """set sdk_token for the connection
        """
        if self.api_thread:
            logger.info("To change SDK tokens, restart the sample app.")
            return
        try:
            if not SPI_CONNECTION:
                self.api_thread = goTenna.driver.Driver(
                    sdk_token=sdk_token,
                    gid=None,
                    settings=None,
                    event_callback=self.event_callback,
                )
            else:
                self.api_thread = goTenna.driver.SpiDriver(
                    SPI_BUS_NO,
                    SPI_CHIP_NO,
                    22,
                    27,
                    sdk_token,
                    None,
                    None,
                    self.event_callback,
                )
            self.api_thread.start()
        except ValueError:
            logger.error(
                f"SDK token {sdk_token} is not valid. Please enter a valid SDK token."
            )
        logger.debug(f"SDK_TOKEN: {self.api_thread.sdk_token.decode('utf-8')}")

    def event_callback(self, evt):
        """ The event callback that will store even messages from the API.
        See the documentation for ``goTenna.driver``.
        This will be invoked from the API's thread when events are received.
        """
        if evt.event_type == goTenna.driver.Event.MESSAGE:
            self.events.msg.put(evt)
            try:
                if self.handle_message_thread.is_alive():
                    pass
                else:
                    self.handle_message_thread.start()
            except Exception:
                traceback.print_exc()
        elif evt.event_type == goTenna.driver.Event.DEVICE_PRESENT:
            self.events.device_present.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                logger.info("Device physically connected")
            else:
                logger.info("Device physically connected, configure to continue")
        elif evt.event_type == goTenna.driver.Event.CONNECT:
            self.events.connect.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                logger.info("Device reconnected! Firmware update complete!")
                self._awaiting_disconnect_after_fw_update[0] = False
            else:
                config.START = time.time()
                logger.info("Connected!")
        elif evt.event_type == goTenna.driver.Event.DISCONNECT:
            self.events.disconnect.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                # Do not reset configuration so that the device will reconnect on its
                # own
                logger.info("Firmware update: Device disconnected, awaiting reconnect")
            else:
                logger.info("Disconnected! {}".format(evt))
                # We reset the configuration here so that if the user plugs in a
                # different device it is not immediately reconfigured with new and
                # incorrect data
                self.api_thread.set_gid(None)
                self.api_thread.set_rf_settings(None)
                self._set_frequencies = False
                self._set_tx_power = False
                self._set_bandwidth = False
        elif evt.event_type == goTenna.driver.Event.STATUS:
            self.status = evt.status
            self.events.status.put(evt)
        elif evt.event_type == goTenna.driver.Event.GROUP_CREATE:
            index = -1
            for idx, member in enumerate(evt.group.members):
                if member.gid_val == self.api_thread.gid.gid_val:
                    index = idx
                    break
            logger.info(
                "Added to group {}: You are member {}".format(
                    evt.group.gid.gid_val, index
                )
            )
            self.events.group_create.put(evt)

    def build_callback(self, error_handler=None, binary=False):
        """ Build a callback for sending to the API thread. May specify a callable
        error_handler(details) taking the error details from the callback.
        The handler should return a string.
        """

        def default_error_handler(details):
            """ Easy error handler if no special behavior is needed.
            Just builds a string with the error.
            """
            if details["code"] in [
                goTenna.constants.ErrorCodes.TIMEOUT,
                goTenna.constants.ErrorCodes.OSERROR,
                goTenna.constants.ErrorCodes.EXCEPTION,
            ]:
                logger.warning("USB connection disrupted")
            logger.error(f"Error: {details['code']}: {details['msg']}")

        # Define a second function here so it implicitly captures self
        captured_error_handler = [error_handler]

        def callback(
            correlation_id,
            success=None,
            results=None,
            error=None,
            details=None,
            binary=binary,
        ):
            """ The default callback to pass to the API.
            See the documentation for ``goTenna.driver``.
            Does nothing but print whether the method succeeded or failed.
            """
            method = self.in_flight_events.pop(correlation_id.bytes, "Method call")
            if success:
                if not binary:
                    if results:
                        result = {
                            "method": method,
                            "results": results,
                            "status": "Success",
                        }
                        self.events.callback.put(result)
                        logger.info(result)
                    else:
                        result = {"method": method, "status": "success"}
                        self.events.callback.put(result)
                        logger.info(result)
                if binary:
                    # TODO: result not being returned for binary payloads
                    pass
                    # if results:
                    #     print("Sent via mesh:\n")
                    #     utilities.hexdump(results)
            elif error:
                if not captured_error_handler[0]:
                    captured_error_handler[0] = default_error_handler
                    result = {
                        "method": method,
                        "error_details": captured_error_handler[0](details),
                        "status": "failed",
                    }
                    self.events.callback.put(result)
                    logger.info(result)

        return callback

    def set_gid(self, gid):
        """ Create a new profile (if it does not already exist) with default settings.
        GID should be a 15-digit numerical GID.
        """
        if self.api_thread.connected:
            logger.info("Must not already be connected when setting GID")
            return
        (_gid, _) = self._parse_gid(gid, goTenna.settings.GID.PRIVATE)
        if not _gid:
            return
        self.api_thread.set_gid(_gid)
        self._settings.gid_settings = gid
        logger.info(f"GID: {self.api_thread.gid.gid_val}")

    @utilities.rate_dec(private=False)
    def send_broadcast(self, message, binary=False):
        """ Send a broadcast message, if binary=True, message must be bytes
        """
        if not self.api_thread.connected:
            logger.error(
                {
                    "send_broadcast": {
                        "status": "failed",
                        "reason": "No device connected",
                    }
                }
            )
        else:

            def error_handler(details):
                """ A special error handler for formatting message failures
                """
                if details["code"] in [
                    goTenna.constants.ErrorCodes.TIMEOUT,
                    goTenna.constants.ErrorCodes.OSERROR,
                ]:
                    logger.error(
                        {
                            "send_broadcast": {
                                "status": "failed",
                                "reason": "message may not have been sent: USB "
                                "connection disrupted",
                            }
                        }
                    )
                logger.error(
                    {
                        "send_broadcast": {
                            "status": "failed",
                            "reason": f"error sending message: {details}",
                        }
                    }
                )

            try:
                if binary:
                    method_callback = self.build_callback(error_handler, binary=True)
                    payload = goTenna.payload.BinaryPayload(message)
                else:
                    method_callback = self.build_callback(error_handler)
                    payload = goTenna.payload.TextPayload(message)

                corr_id = self.api_thread.send_broadcast(payload, method_callback)
                while corr_id is None:
                    # try again if send_broadcast fails
                    time.sleep(10)
                    corr_id = self.api_thread.send_broadcast(payload, method_callback)

                self.in_flight_events[
                    corr_id.bytes
                ] = f"Broadcast message: {message} ({len(message)} bytes)\n"
                self.bytes_sent += len(message)
                logger.info(
                    f"Sent {colored(utilities.naturalsize(len(message)), 'magenta')}"
                )

                if binary:
                    # utilities.hexdump(message, send=True)
                    ...
            except ValueError:
                logger.error(
                    {
                        "send_broadcast": {
                            "status": "failed",
                            "reason": "message too long!",
                        }
                    }
                )
            if not binary:
                logger.info(
                    {
                        "send_broadcast": {
                            "status": "complete",
                            "message": message,
                            "size(B)": len(message),
                        }
                    }
                )

    @staticmethod
    def _parse_gid(__gid, gid_type, print_message=True):
        try:
            if __gid > goTenna.constants.GID_MAX:
                logger.error(
                    f"{str(__gid)} is not a valid GID. The maximum GID is "
                    f"{str(goTenna.constants.GID_MAX)}"
                )
                return None, __gid
            gidobj = goTenna.settings.GID(__gid, gid_type)
            return gidobj, None
        except ValueError:
            if print_message:
                logger.error(f"{__gid} is not a valid GID.")
            return None, None

    @utilities.rate_dec(private=True)
    def send_private(self, gid: int, message, binary=False):
        """ Send a private message to a contact
        GID is the GID to send the private message to.
        """
        _gid, rest = self._parse_gid(gid, goTenna.settings.GID.PRIVATE)
        if not self.api_thread.connected:
            logger.warning("Must connect first")
            return
        if not _gid:
            return

        def error_handler(details):
            """ Special error handler for sending private messages to format errors
            """
            return f"Error sending message: {details}"

        try:
            if binary:
                method_callback = self.build_callback(error_handler, binary=True)
                payload = goTenna.payload.BinaryPayload(message)
            else:
                method_callback = self.build_callback(error_handler)
                payload = goTenna.payload.TextPayload(message)

            def ack_callback(correlation_id, success):
                if not success:
                    logger.error(
                        f"Private message to {_gid.gid_val}: delivery not confirmed,"
                        f"recipient may be offline or out of range"
                    )

            corr_id = self.api_thread.send_private(
                _gid,
                payload,
                method_callback,
                ack_callback=ack_callback,
                # encrypt=self._do_encryption,
                encrypt=False,
            )
        except ValueError:
            logger.error("Message too long!")
            return
        self.in_flight_events[
            corr_id.bytes
        ] = f"Private message to {_gid.gid_val}: {message}"
        digest = sha256(message).hexdigest()
        if config.DEBUG:
            logger.info(
                colored(
                    f"Sent {utilities.naturalsize(len(message))} - {digest}", "magenta"
                )
            )
        else:
            logger.info(
                colored(f"Sent {utilities.naturalsize(len(message))}", "magenta")
            )
        utilities.hexdump(message, send=True)

    def send_jumbo(self, message, segment_size=210, private=False, gid=None):
        msg_segments = utilities.segment(message, segment_size)
        logger.info(f"Created segmented message with {len(msg_segments)} segments")
        # extra sanity check that we don't relay messages larger than ~1 KB
        if len(msg_segments) > 12:
            logger.info(
                f"Message of {len(msg_segments)} segments too long for jumbo send. "
                f"Not sending"
            )
            return
        if not private:
            i = 0
            for msg in msg_segments:
                i += 1
                time.sleep(2)
                self.send_broadcast(msg)
                # logger.info(f"Sent message utilities.segment {i} of {len(msg_segments)}")
        return
        # disabled for now as requires custom message parsing
        # TODO: enable private messages here
        # if not gid:
        #     print("Missing GID")
        #     return
        # gid = goTenna.settings.GID(gid, 0)
        # for msg in msg_segments:
        #     self.send_private(gid, msg)

    def get_device_type(self):
        device = self.api_thread.device_type
        logger.info(device)
        return device

    @staticmethod
    def list_geo_region():
        """ List the available region.
        """
        return goTenna.constants.GEO_REGION.DICT

    def set_geo_region(self, region):
        """ Configure the frequencies the device will use.
        Allowed region displayed with list_geo_region.
        """
        if self.get_device_type() == "pro":
            logger.error("This configuration cannot be done for Pro devices.")
            return
        if not goTenna.constants.GEO_REGION.valid(region):
            logger.error("Invalid region setting {}".format(region))
            return
        self._set_geo_region = True
        self._settings.geo_settings.region = region
        self.api_thread.set_geo_settings(self._settings.geo_settings)
        logger.info(f"GEO_REGION: {self.api_thread.geo_settings.region}")

    def can_connect(self):
        """ Return whether a goTenna can connect.
        For a goTenna to connect, a GID and RF settings must be configured.
        """
        result = {}
        if self.api_thread.gid:
            result["GID"] = "OK"
        else:
            result["GID"] = "Not Set"
        if self._set_tx_power:
            result["PRO - TX Power"] = "OK"
        else:
            result["PRO - TX Power"] = "Not Set"
        if self._set_frequencies:
            result["PRO - Frequencies"] = "OK"
        else:
            result["PRO - Frequencies"] = "Not Set"
        if self._set_bandwidth:
            result["PRO - Bandwidth"] = "OK"
        else:
            result["PRO - Bandwidth"] = "Not Set"
        if self._set_geo_region:
            result["MESH - Geo region"] = "OK"
        else:
            result["MESH - Geo region"] = "Not Set"
        logger.info(result)
        return result

    def get_system_info(self):
        """ Get system information.
        """
        if not self.api_thread.connected:
            logger.info("Device must be connected")
            return
        info = {"SYSTEM_INFO": self.api_thread.system_info}
        logger.info(info)
        return info
