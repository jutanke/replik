# Scheduling

## Getting started
A replik project provides simple scaffolding to encapsulate a project within a schedulable docker environment.
This way projects become *schedulable* and hardware resources can be allocated as needed.
Most importantly, docker ensures that only the requested resources (cpu, memory, gpu) are utilized.

To get started, a **replik** project has to be initialized.
Two options are available:
* **simple project**: unintrusive, can be used to *replik-ify* exisiting projects
* **replik-python project**: provides a bit more scaffolding for python projects
