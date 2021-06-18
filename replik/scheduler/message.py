from enum import IntEnum
from typing import Dict


class MsgType(IntEnum):
    ALIVE = 1
    REQUEST_UID = 2
    SEND_UID = 3
    SEND_PROCESS = 4


def get_is_alive_msg():
    return {"msg": MsgType.ALIVE}


def get_request_uid_msg():
    return {"msg": MsgType.REQUEST_UID}


def get_process_msg(uid, info: Dict):
    return {"msg": MsgType.SEND_PROCESS, "info": info, "uid": uid}


def get_msg_type(msg):
    return msg["msg"]
