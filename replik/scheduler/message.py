from enum import IntEnum
from typing import Dict


class MsgType(IntEnum):
    ALIVE = 1
    REQUEST_UID = 2
    SEND_UID = 3
    REQUEST_MURDER = 4
    # RESP_PROCESS = 5


def get_is_alive_msg():
    return {"msg": MsgType.ALIVE}


def get_murder_msg(uid):
    return {"msg": MsgType.REQUEST_MURDER, "uid": uid}


def get_request_uid_msg(info):
    return {"msg": MsgType.REQUEST_UID, "info": info}


def get_msg_type(msg):
    return msg["msg"]
