import logging
import re
import sys
import threading
import time
from enum import IntEnum
from pathlib import Path
from typing import Any

import cffi
import keyring

from anime_rpc.cli import CLI_ARGS
from anime_rpc.config import DEFAULT_APPLICATION_ID

DISCORD_API_PATTERN = re.compile(r"\bDISCORD_API\b")
PREPROCESSOR_LINE_PATTERN = re.compile("^#.*$", re.MULTILINE)
CPPLUS_BLOCK_PATTERN = re.compile(
    r"^#ifdef __cplusplus\s.*?\s#endif$", re.MULTILINE | re.DOTALL
)
SCOPES = "sdk.social_layer_presence openid"
SERVICE_NAME = "anime_rpc"
MAX_BUTTONS = 2


def strip_preprocessor_directives(header_text: str) -> str:
    # this is a dumb filter so it may break at any time
    header_text = header_text.replace("\r\n", "\n")
    header_text = DISCORD_API_PATTERN.sub("", header_text)
    header_text = CPPLUS_BLOCK_PATTERN.sub("", header_text)
    header_text = PREPROCESSOR_LINE_PATTERN.sub("", header_text)
    return header_text


_LOGGER = logging.getLogger("social_sdk")
INCLUDE_PATH = Path(__file__).parent / "../include"
LIB_PATH = Path(__file__).parent / "../lib"

if sys.platform == "win32":
    LIB_NAME = "discord_partner_sdk.dll"
elif sys.platform == "linux":
    LIB_NAME = "libdiscord_partner_sdk.so"  # type: ignore[reportConstantRedefinition]
elif sys.platform == "darwin":
    LIB_NAME = "libdiscord_partner_sdk.dylib"  # type: ignore[reportConstantRedefinition]
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")

ffi = cffi.FFI()
ffi.cdef(strip_preprocessor_directives((INCLUDE_PATH / "cdiscord.h").read_text()))
C = ffi.dlopen(str(LIB_PATH / LIB_NAME))


def _dec_c_str(msg: cffi.FFI.CData) -> str:
    if not msg or not msg.ptr:  # type: ignore
        return ""
    byte_string = ffi.buffer(msg.ptr, msg.size)[:]  # type: ignore
    return byte_string.decode("utf-8")  # type: ignore


def _enc_c_str(msg: str) -> tuple[cffi.FFI.CData, cffi.FFI.CData]:
    if not msg:
        return ffi.NULL, ffi.NULL  # type: ignore

    byte_string = msg.encode("utf-8")
    buffer = ffi.new("char[]", byte_string)  # type: ignore
    discord_string_ptr = ffi.new(  # type: ignore
        "Discord_String *",
        {
            "ptr": ffi.cast("uint8_t *", buffer),  # type: ignore
            "size": len(byte_string),  # type: ignore
        },
    )
    return discord_string_ptr, buffer  # type: ignore


def _handle_discord_error(
    scope: str, error: cffi.FFI.CData, convert: cffi.FFI.CData
) -> None:
    error_ptr = ffi.new("Discord_String *")  # type: ignore
    convert(error, error_ptr)  # type: ignore
    error_str = _dec_c_str(error_ptr[0])  # type: ignore
    _LOGGER.error("%s error: %s", scope, error_str or "unknown error")


class LoggingSeverity(IntEnum):
    VERBOSE = 1
    INFO = 2
    WARNING = 3
    ERROR = 4
    NONE = 5


@ffi.callback("void(Discord_String, Discord_LoggingSeverity, void *)")
def _log_callback(message_struct, severity, user_data) -> None:  # type: ignore
    message = _dec_c_str(message_struct).strip()  # type: ignore
    severity = LoggingSeverity(severity)
    instance = ffi.from_handle(user_data)  # type: ignore

    assert isinstance(message, str)
    if severity == LoggingSeverity.ERROR:
        _LOGGER.error("Log callback: %s", message)
    else:
        _LOGGER.debug("Log callback: %s", message)

    if (
        "RPC Connect error: -4058" in message
        and not instance.sent_disconnection_warning
    ):
        _LOGGER.error("Disconnected! Is Discord running?")
        instance.sent_disconnection_warning = True
    elif "RPC manager connected" in message:
        instance.sent_disconnection_warning = False
        _LOGGER.info("Connected to Discord!")
        if instance.current_activity:
            _LOGGER.info("Restoring current activity...")
            instance.set_activity(**instance.current_activity)  # type: ignore


@ffi.callback("void(Discord_Client_Status, Discord_Client_Error, int32_t, void *)")
def _status_changed_callback(status, error, error_detail, user_data):  # type: ignore
    status_ptr = ffi.new("Discord_String *")  # type: ignore
    C.Discord_Client_StatusToString(status, status_ptr)  # type: ignore
    _LOGGER.debug("Status changed: %s", _dec_c_str(status_ptr[0]))  # type: ignore

    if status == C.Discord_Client_Status_Ready:  # type: ignore
        _LOGGER.info("Discord client is ready")
    elif status == C.Discord_Client_Status_Disconnected:  # type: ignore
        _LOGGER.info("Discord client is disconnected")
    elif error != C.Discord_Client_Error_None:  # type: ignore
        _handle_discord_error(
            "Status changed",
            error,  # type: ignore
            C.Discord_Client_ErrorToString,  # type: ignore
        )


@ffi.callback("void(Discord_ClientResult *, Discord_String, Discord_String, void *)")
def _authorize_callback(result_ptr, code, redirect_uri, user_data):  # type: ignore
    instance = ffi.from_handle(user_data)  # type: ignore

    if C.Discord_ClientResult_Successful(result_ptr):  # type: ignore
        _LOGGER.info("Getting access token...")

        verifier_str_ptr = ffi.new("Discord_String *")  # type: ignore
        C.Discord_AuthorizationCodeVerifier_Verifier(  # type: ignore
            instance.code_verifier, verifier_str_ptr
        )
        C.Discord_Client_GetToken(  # type: ignore
            instance.client,
            instance.last_application_id,
            code,
            verifier_str_ptr[0],
            redirect_uri,
            _token_exchange_callback,
            ffi.NULL,
            instance.self_handle,
        )
        return

    _handle_discord_error("Authorization", result_ptr, C.Discord_ClientResult_Error)  # type: ignore


@ffi.callback(
    "void(Discord_ClientResult *, Discord_String, Discord_String, Discord_AuthorizationTokenType, int32_t, Discord_String, void *)"
)
def _token_exchange_callback(
    result_ptr,  # type: ignore
    access_token,  # type: ignore
    refresh_token,  # type: ignore
    token_type,  # type: ignore
    expires_in,  # type: ignore
    scopes,  # type: ignore
    user_data,  # type: ignore
):
    instance = ffi.from_handle(user_data)  # type: ignore

    if C.Discord_ClientResult_Successful(result_ptr):  # type: ignore
        _LOGGER.info("Access token received! Connecting...")
        C.Discord_Client_UpdateToken(  # type: ignore
            instance.client,
            token_type,
            access_token,
            _update_token_callback,
            ffi.NULL,
            instance.self_handle,
        )
        keyring.set_password(
            SERVICE_NAME,
            f"refresh_token:{instance.last_application_id}",
            _dec_c_str(refresh_token),  # type: ignore
        )
        return

    _handle_discord_error("Get token", result_ptr, C.Discord_ClientResult_Error)  # type: ignore


@ffi.callback("void(Discord_ClientResult *, void *)")
def _update_token_callback(result_ptr, user_data):  # type: ignore
    instance = ffi.from_handle(user_data)  # type: ignore

    if C.Discord_ClientResult_Successful(result_ptr):  # type: ignore
        _LOGGER.info("Token updated, connecting to Discord...")
        C.Discord_Client_Connect(instance.client)  # type: ignore
        return

    _handle_discord_error("Update token", result_ptr, C.Discord_ClientResult_Error)  # type: ignore


@ffi.callback("void(Discord_ClientResult *, void *)")
def _update_presence_callback(result_ptr, user_data):  # type: ignore
    if C.Discord_ClientResult_Successful(result_ptr):  # type: ignore
        _LOGGER.debug("Presence updated!")
        return

    _handle_discord_error(
        "Update presence",
        result_ptr,  # type: ignore
        C.Discord_ClientResult_Error,  # type: ignore
    )


class Discord:
    def __init__(self) -> None:
        self.last_application_id = None
        self.client = None  # type: ignore
        self.thread: threading.Thread | None = None
        self.code_verifier = None
        self.self_handle = ffi.new_handle(self)
        self.sent_disconnection_warning = False
        self.current_activity: dict[str, Any] = {}

    def _create_options(self) -> cffi.FFI.CData:
        options = ffi.new("Discord_ClientCreateOptions*")  # type: ignore
        C.Discord_ClientCreateOptions_Init(options)  # type: ignore
        return options

    def init(self) -> None:
        if self.client is not None:
            raise RuntimeError("Discord client is already initialised")
        _LOGGER.debug(
            "Initializing Discord client, with app id: %d", DEFAULT_APPLICATION_ID
        )
        self.client = ffi.new("Discord_Client*")  # type: ignore
        options = self._create_options()
        C.Discord_Client_InitWithOptions(self.client, options)  # type: ignore
        C.Discord_Client_AddLogCallback(  # type: ignore
            self.client,
            _log_callback,
            ffi.NULL,
            self.self_handle,
            C.Discord_LoggingSeverity_Verbose,  # type: ignore
        )
        C.Discord_Client_SetStatusChangedCallback(  # type: ignore
            self.client,
            _status_changed_callback,
            ffi.NULL,
            self.self_handle,
        )
        self.set_application_id(DEFAULT_APPLICATION_ID)

    def set_application_id(self, application_id: int) -> None:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")

        if application_id != self.last_application_id:
            _LOGGER.debug("Setting application id: %d", application_id)
            C.Discord_Client_SetApplicationId(self.client, application_id)  # type: ignore
            self.last_application_id = application_id
            _ = (
                CLI_ARGS.use_oauth2
                and not self.try_authorize_with_stored_token()
                and self.authorize()
            )

    def try_authorize_with_stored_token(self) -> bool:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")
        if self.last_application_id is None:
            raise RuntimeError("Application ID is not set")

        refresh_token = keyring.get_password(
            SERVICE_NAME, f"refresh_token:{self.last_application_id}"
        )
        if not refresh_token:
            _LOGGER.info("No stored refresh token found")
            return False

        _LOGGER.info("Stored refresh token found, trying to authorize...")

        ptr, _buf = _enc_c_str(refresh_token)
        C.Discord_Client_RefreshToken(  # type: ignore
            self.client,
            self.last_application_id,
            ptr[0],
            _token_exchange_callback,
            ffi.NULL,
            self.self_handle,
        )
        return True

    def drop(self) -> None:
        _LOGGER.debug("Dropping Discord client")
        C.Discord_Client_Drop(self.client)  # type: ignore
        self.client = None

    def start(self, threaded: bool = True) -> None:
        if self.client is None:
            self.init()

        if threaded:
            _LOGGER.debug("Starting internal loop")
            self.thread = threading.Thread(target=self.start, args=(False,))
            self.thread.start()
            return

        while self.client is not None:  # type: ignore
            C.Discord_RunCallbacks()  # type: ignore
            time.sleep(1 / 100)

    def stop(self) -> None:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")
        _LOGGER.debug("Stopping internal loop")
        self.drop()  # type: ignore
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    def authorize(self) -> None:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")

        _LOGGER.info("Starting authorization flow...")

        self.code_verifier = ffi.new("Discord_AuthorizationCodeVerifier*")  # type: ignore
        C.Discord_Client_CreateAuthorizationCodeVerifier(  # type: ignore
            self.client,
            self.code_verifier,
        )

        args = ffi.new("Discord_AuthorizationArgs *")  # type: ignore
        C.Discord_AuthorizationArgs_Init(args)  # type: ignore
        C.Discord_AuthorizationArgs_SetClientId(args, self.last_application_id)  # type: ignore

        ptr, _buf = _enc_c_str(SCOPES)
        C.Discord_AuthorizationArgs_SetScopes(args, ptr[0])  # type: ignore

        challenge_ptr = ffi.new("Discord_AuthorizationCodeChallenge *")  # type: ignore
        C.Discord_AuthorizationCodeVerifier_Challenge(self.code_verifier, challenge_ptr)  # type: ignore
        C.Discord_AuthorizationArgs_SetCodeChallenge(args, challenge_ptr)  # type: ignore
        C.Discord_Client_Authorize(  # type: ignore
            self.client, args, _authorize_callback, ffi.NULL, self.self_handle
        )

    def set_activity(
        self,
        state: str,
        details: str,
        type_: int = 0,
        small_text: str = "",
        small_image: str = "",
        large_text: str = "",
        large_image: str = "",
        buttons: list[dict[str, str]] | None = None,
        start: int = 0,
        end: int = 0,
        status_display_type: int = 0,
    ) -> None:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")

        self.current_activity = {
            "state": state,
            "details": details,
            "type_": type_,
            "small_text": small_text,
            "small_image": small_image,
            "large_text": large_text,
            "large_image": large_image,
            "buttons": buttons,
            "start": start,
            "end": end,
            "status_display_type": status_display_type,
        }
        _LOGGER.debug("Current activity: %s", self.current_activity)

        garbage_buffers: list[cffi.FFI.CData] = []
        activity = ffi.new("Discord_Activity *")  # type: ignore
        C.Discord_Activity_Init(activity)  # type: ignore
        C.Discord_Activity_SetType(activity, type_)  # type: ignore

        ptr, buf = _enc_c_str(state)
        if ptr != ffi.NULL:  # type: ignore
            C.Discord_Activity_SetState(activity, ptr)  # type: ignore
            garbage_buffers.append(buf)

        ptr, buf = _enc_c_str(details)
        if ptr != ffi.NULL:  # type: ignore
            C.Discord_Activity_SetDetails(activity, ptr)  # type: ignore
            garbage_buffers.append(buf)

        if start > 0:
            timestamps = ffi.new("Discord_ActivityTimestamps *")  # type: ignore
            C.Discord_ActivityTimestamps_Init(timestamps)  # type: ignore
            C.Discord_ActivityTimestamps_SetStart(timestamps, start)  # type: ignore
            if end > 0:
                C.Discord_ActivityTimestamps_SetEnd(timestamps, end)  # type: ignore
            C.Discord_Activity_SetTimestamps(activity, timestamps)  # type: ignore

        if large_image or large_text or small_image or small_text:
            assets = ffi.new("Discord_ActivityAssets *")  # type: ignore
            C.Discord_ActivityAssets_Init(assets)  # type: ignore

            def set_asset(
                text: str,
                image: str,
                text_setter: cffi.FFI.CData,
                image_setter: cffi.FFI.CData,
            ) -> None:
                ptr, buf = _enc_c_str(text)
                if ptr != ffi.NULL:  # type: ignore
                    garbage_buffers.append(buf)
                    text_setter(assets, ptr)

                ptr, buf = _enc_c_str(image)
                if ptr != ffi.NULL:  # type: ignore
                    garbage_buffers.append(buf)
                    image_setter(assets, ptr)

            set_asset(
                large_text,
                large_image,
                C.Discord_ActivityAssets_SetLargeText,  # type: ignore
                C.Discord_ActivityAssets_SetLargeImage,  # type: ignore
            )
            set_asset(
                small_text,
                small_image,
                C.Discord_ActivityAssets_SetSmallText,  # type: ignore
                C.Discord_ActivityAssets_SetSmallImage,  # type: ignore
            )

            C.Discord_Activity_SetAssets(activity, assets)  # type: ignore

        if buttons:
            if len(buttons) > MAX_BUTTONS:
                _LOGGER.warning(
                    "Too many buttons (%d), truncating to %d",
                    len(buttons),
                    MAX_BUTTONS,
                )
                buttons = buttons[:MAX_BUTTONS]

        for button_data in buttons or ():
            label = button_data.get("label")
            url = button_data.get("url")

            if not label or not url:
                continue

            c_button = ffi.new("Discord_ActivityButton *")  # type: ignore
            C.Discord_ActivityButton_Init(c_button)  # type: ignore

            ptr, buf = _enc_c_str(label)
            C.Discord_ActivityButton_SetLabel(c_button, ptr[0])  # type: ignore
            garbage_buffers.append(buf)

            ptr, buf = _enc_c_str(url)
            C.Discord_ActivityButton_SetUrl(c_button, ptr[0])  # type: ignore
            garbage_buffers.append(buf)

            C.Discord_Activity_AddButton(activity, c_button)  # type: ignore

        if status_display_type > 0:
            c_display_type = ffi.new(  # type: ignore
                "Discord_StatusDisplayTypes *", status_display_type
            )
            C.Discord_Activity_SetStatusDisplayType(activity, c_display_type)  # type: ignore

        C.Discord_Client_UpdateRichPresence(  # type: ignore
            self.client,
            activity,
            _update_presence_callback,  # type: ignore
            ffi.NULL,
            self.self_handle,
        )

    def clear_activity(self) -> None:
        if self.client is None:
            raise RuntimeError("Discord client is not initialised")

        _LOGGER.debug("Received clear activity request, resetting current activity")
        self.current_activity = {}
        C.Discord_Client_ClearRichPresence(  # type: ignore
            self.client,
        )
