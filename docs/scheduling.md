# Scheduling

## Check currently scheduled resources
To get an overview of the scheduling system and free resources simply
```
replik schedule-info
```
which will return outputs that look like this:
```
~ ~ free / total resources ~ ~
cpus:    4 / 12
gpus:    2 / 4
memory:  20 / 52

~ ~ staging (#0) ~ ~
uid | docker tag | waiting time ~ ~


~ ~ running (#1) ~ ~
uid | docker tag | running time | gpus

000000 | julian_tanke/replik_demo | 32 min | [0, 1]
```
**staging** lists all processes that are waiting to be scheduled (and for how long they are waiting) while **running** lists all currently running processes with their utilized GPUS + running time.


## Getting started
A replik project provides simple scaffolding to encapsulate a project within a schedulable docker environment.
This way projects become *schedulable* and hardware resources can be allocated as needed.
Most importantly, docker ensures that only the requested resources (cpu, memory, gpu) are utilized.

To get started, a **replik** project has to be initialized.
Lets start with a simple sample project which has the following structure:

* ```{root}/sample```
  * ```sample.sh```

where ```sample.sh``` contains:
```bash
echo "hello world $1 $2"
```

we now ```cd {root}/sample``` and intialize the project:
```
replik init-simple
```
A prompt opens and asks about the project name which we set to ```simple```.
To schedule the script we simply
```
replik schedule --script="sample.sh hi ho"
```
Once the resources are free the project is being scheduled and we see as output ```hello world hi ho```.
