import replik.console as console
import replik.scheduler.client as client


def execute(uid):
    if len(uid) == 0:
        console.fail("you need to pass a {uid} for unscheduling..")
        console.info("for example: \n\t$ replik unschedule --uid=1")
        exit()

    client.request_to_kill_uid(int(uid))
