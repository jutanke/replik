# Scheduling

The scheduling is file-based and each process-to-be-scheduled is represented as single file!
Under ```/srv/replik_schedule``` we employ the following folder structure:
* ```/srv/replik_schedule/staging``` is where processes place their request for being scheduled, along with their hardware requirements. This folder is being populated by the respective users that want their scripts to be scheduled.
* ```/srv/replik_schedule/running``` is where currently running processes are placed. This may only be utilized by the scheduler!