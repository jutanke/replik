# Structure 

Any replik project is made up of these files:
* ```{root}/docker```
  * ```Dockerfile```: normal Dockerfile that defines the container
  * ```hook_pre_useradd```: any ```RUN``` command for the Dockerfile that should be executed before the user for building the container is switched from ```root``` to the current user.
  * ```hook_post_useradd```: any ```RUN``` command for the Dockerfile where the user should be the actual user.
  * ```bashhook.sh```: script that is being called whenever a container starts.
* ```{root}/.replik```
  * ```info.json```: information about this replik project
    * ```cpus```: amount of cpus that this project should use when scheduled
    * ```gpus```: amount of gpus that this project should use when scheduled
    * ```memory```: amount of memory that this project should use when scheduled
    * ```minimum_required_running_hours```: minimal amount of time that that a project needs to run un-interruptedly. If a container for this project is scheduled and running and exceeds this time it may be killed to schedule new processes.
    * ```stdout_to_file```: If true stdout/stderr will be forwarded to a file

