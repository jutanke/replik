import replik.console as console
from replik.scheduler.client import request_server_infos


def execute():
    status = request_server_infos()

    free_res = status["free"]
    total_res = status["total"]
    console.info("\n~ ~ free / total resources ~ ~")
    console.info(f"cpus:    {free_res['cpus']} / {total_res['cpus']}")
    console.info(f"gpus:    {free_res['gpus']} / {total_res['gpus']}")
    console.info(f"memory:  {free_res['mem']} / {total_res['mem']}")

    staging_queue = status["staging"]
    console.warning(
        f"\n~ ~ staging (#{len(staging_queue)}) ~ ~\nuid | docker tag | waiting time ~ ~\n"
    )
    for proc in staging_queue:
        line = f"%06d | {proc['info']['tag']} | " % (proc["info"]["uid"])
        wtime = proc["waiting_in_h"]
        if wtime > 2:
            line += "%03.02f h" % wtime
        else:
            line += f"{int(60 * wtime)} min"
        console.warning(line)

    running_queue = status["running"]
    console.success(f"\n~ ~ running (#{len(running_queue)}) ~ ~")
    console.success("uid | docker tag | running time | gpus\n")

    for proc in running_queue:
        line = f"%06d | {proc['info']['tag']} | " % (proc["info"]["uid"])
        rtime = proc["running_in_h"]
        if rtime > 2:
            line += "%03.02f h | " % rtime
        else:
            line += f"{int(60 * rtime)} min | "
        line += f"{proc['gpus']}"
        console.success(line)

    print("\n")
