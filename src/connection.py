import logging
import threading
import traceback
from pprint import pprint
from time import sleep

import goTenna

from events import Events
from messages import handle_message
from utilities import cli, segment
from gotenna_sockets import start_socket
from config import CONFIG

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format=CONFIG["logging"]["FORMAT"])
# mute some of the other noisy loggers
logging.getLogger("goTenna").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.INFO)

# For SPI connection only, set SPI_CONNECTION to true with proper SPI settings
SPI_CONNECTION = False
SPI_BUS_NO = 0
SPI_CHIP_NO = 0
SPI_REQUEST = 22
SPI_READY = 27


class Connection:
    def __init__(self):  # host, port, listen):
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
        self.events = Events()
        self.service_url = None
        self.swap_payment_hash = None
        self.swap_preimage = None
        self.gateway = 0
        self.jumbo_thread = threading.Thread()
        self.cli = False
        # self.socket = start_socket(self, host, port, listen)

    def reset_connection(self):
        if self.api_thread:
            self.api_thread.join()
        self.__init__()

    @cli
    def sdk_token(self, sdk_token):
        """set sdk_token for the connection
        """
        if self.api_thread:
            self.log("To change SDK tokens, restart the sample app.")
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
            self.log(
                f"SDK token {sdk_token} is not valid. Please enter a valid SDK token."
            )
        self.log(f"SDK_TOKEN: {self.api_thread.sdk_token.decode('utf-8')}")

    def event_callback(self, evt):
        """ The event callback that will store even messages from the API.
        See the documentation for ``goTenna.driver``.
        This will be invoked from the API's thread when events are received.
        """
        if evt.event_type == goTenna.driver.Event.MESSAGE:
            self.events.msg.put(evt)
            try:
                thread = threading.Thread(
                    target=handle_message, args=[self, evt.message]
                )
                thread.start()
            except Exception:
                traceback.print_exc()
        elif evt.event_type == goTenna.driver.Event.DEVICE_PRESENT:
            self.events.device_present.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                self.log("Device physically connected")
            else:
                self.log("Device physically connected, configure to continue")
        elif evt.event_type == goTenna.driver.Event.CONNECT:
            self.events.connect.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                self.log("Device reconnected! Firmware update complete!")
                self._awaiting_disconnect_after_fw_update[0] = False
            else:
                self.log("Connected!")
        elif evt.event_type == goTenna.driver.Event.DISCONNECT:
            self.events.disconnect.put(evt)
            if self._awaiting_disconnect_after_fw_update[0]:
                # Do not reset configuration so that the device will reconnect on its
                # own
                self.log("Firmware update: Device disconnected, awaiting reconnect")
            else:
                self.log("Disconnected! {}".format(evt))
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
            self.log(
                "Added to group {}: You are member {}".format(
                    evt.group.gid.gid_val, index
                )
            )
            self.events.group_create.put(evt)

    def build_callback(self, error_handler=None):
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
                self.log("USB connection disrupted")
            self.log(f"Error: {details['code']}: {details['msg']}")

        # Define a second function here so it implicitly captures self
        captured_error_handler = [error_handler]

        def callback(
            correlation_id, success=None, results=None, error=None, details=None
        ):
            """ The default callback to pass to the API.
            See the documentation for ``goTenna.driver``.
            Does nothing but print whether the method succeeded or failed.
            """
            method = self.in_flight_events.pop(correlation_id.bytes, "Method call")
            if success:
                if results:
                    result = {"method": method, "results": results, "status": "Success"}
                    self.events.callback.put(result)
                    self.log(result)
                else:
                    result = {"method": method, "status": "success"}
                    self.events.callback.put(result)
                    self.log(result)
            elif error:
                if not captured_error_handler[0]:
                    captured_error_handler[0] = default_error_handler
                    result = {
                        "method": method,
                        "error_details": captured_error_handler[0](details),
                        "status": "failed",
                    }
                    self.events.callback.put(result)
                    self.log(result)

        return callback

    def set_gid(self, gid):
        """ Create a new profile (if it does not already exist) with default settings.
        GID should be a 15-digit numerical GID.
        """
        if self.api_thread.connected:
            self.log("Must not be connected when setting GID")
            return
        (_gid, _) = self._parse_gid(gid, goTenna.settings.GID.PRIVATE)
        if not _gid:
            return
        self.api_thread.set_gid(_gid)
        self._settings.gid_settings = gid
        self.log(f"GID: {self.api_thread.gid.gid_val}")

    def send_broadcast(self, message):
        """ Send a broadcast message
        """
        if not self.api_thread.connected:
            self.log(
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
                    self.log(
                        {
                            "send_broadcast": {
                                "status": "failed",
                                "reason": "message may not have been sent: USB "
                                          "connection disrupted",
                            }
                        }
                    )
                self.log(
                    {
                        "send_broadcast": {
                            "status": "failed",
                            "reason": f"error sending message: {details}",
                        }
                    }
                )

            try:
                method_callback = self.build_callback(error_handler)
                payload = goTenna.payload.TextPayload(message)
                self.log(
                    f"payload valid = {payload.valid}, message size = {len(message)}\n"
                )

                corr_id = self.api_thread.send_broadcast(payload, method_callback)
                while corr_id is None:
                    # try again if send_broadcast fails
                    sleep(10)
                    corr_id = self.api_thread.send_broadcast(payload, method_callback)

                self.in_flight_events[
                    corr_id.bytes
                ] = f"Broadcast message: {message} ({len(message)} bytes)\n"
            except ValueError:
                self.log(
                    {
                        "send_broadcast": {
                            "status": "failed",
                            "reason": "message too long!",
                        }
                    }
                )
            self.log(
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
                print(
                    "{} is not a valid GID. The maximum GID is {}".format(
                        str(__gid), str(goTenna.constants.GID_MAX)
                    )
                )
                return None, __gid
            gidobj = goTenna.settings.GID(__gid, gid_type)
            return gidobj, None
        except ValueError:
            if print_message:
                print("{} is not a valid GID.".format(__gid))
            return None, None

    def send_private(self, gid, message):
        """ Send a private message to a contact
        GID is the GID to send the private message to.
        """
        if not self.api_thread.connected:
            print("Must connect first")
            return
        if not gid:
            return

        def error_handler(details):
            """ Special error handler for sending private messages to format errors
            """
            return "Error sending message: {}".format(details)

        try:
            method_callback = self.build_callback(error_handler)
            payload = goTenna.payload.TextPayload(message)

            def ack_callback(correlation_id, success):
                if success:
                    print(
                        "Private message to {}: delivery confirmed".format(gid.gid_val)
                    )
                else:
                    print(
                        "Private message to {}: delivery not confirmed, recipient may"
                        " be offline or out of range".format(gid.gid_val)
                    )

            corr_id = self.api_thread.send_private(
                gid,
                payload,
                method_callback,
                ack_callback=ack_callback,
                encrypt=self._do_encryption,
            )
        except ValueError:
            print("Message too long!")
            return
        self.in_flight_events[corr_id.bytes] = "Private message to {}: {}".format(
            gid.gid_val, message
        )

    def send_jumbo(self, message, segment_size=210, private=False, gid=None):
        msg_segments = segment(message, segment_size)
        self.log(f"Created segmented message with {len(msg_segments)} segments")
        if not private:
            i = 0
            for msg in msg_segments:
                i += 1
                sleep(2)
                self.send_broadcast(msg)
                self.log(f"Sent message segment {i} of {len(msg_segments)}")
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
        self.log(device)
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
            self.log("This configuration cannot be done for Pro devices.")
            return
        if not goTenna.constants.GEO_REGION.valid(region):
            self.log("Invalid region setting {}".format(region))
            return
        self._set_geo_region = True
        self._settings.geo_settings.region = region
        self.api_thread.set_geo_settings(self._settings.geo_settings)
        self.log(f"GEO_REGION: {self.api_thread.geo_settings.region}")

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
        self.log(result)
        return result

    def get_system_info(self):
        """ Get system information.
        """
        if not self.api_thread.connected:
            self.log("Device must be connected")
            return
        info = {"SYSTEM_INFO": self.api_thread.system_info}
        self.log(info)
        return info

    def log(self, message):
        if self.cli:
            pprint(message)
        else:
            logger.debug(message)
