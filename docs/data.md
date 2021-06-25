# Data

All files that are written from within the container are owned by the user that started the process and NOT by root!

## Passing data to the container
You can pass folders that are accessable at host level by creating a file ```{root}/.replik/paths.json```.
This file must contain a list of strings representing paths.
The paths can be either absolute paths OR names without any "/" in them.
In the later case the folder will be expanded to the current project dir.

All paths will be mounted into the container under
```
/home/user/{folder_name}
```
where ```{folder_name}``` is the basename of the path.
Please note that you **cannot** pass symlinked directories to docker! 

### Mapping the data to a specific folder
Often data has to be at a certain location within a file structure.
This can be achived by simply creating a symlink using the ```bashhook.sh``` in the ```docker``` folder, e.g.
```bash
echo "bashhook"
ln -s /home/user/{folder_name} /home/user/{project}/data/where/its/supposed/to/be
```
This technique can also be used to change the basename of the data folder.
