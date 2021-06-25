# Scheduling

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
