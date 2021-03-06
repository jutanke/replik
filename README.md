# replik
Create reproducible environments for deep learning/computer vision research for osx/linux based on docker.

#### Single-User setup
To install the latest version of _replik_ simply clone this repository and run the install script:
```
git clone git@github.com:jutanke/replik.git ~/.replik
cd ~/.replik && pip install -r requirements.txt
```

To automatically install replik simply:
```
cd ~/.replik
bash install.sh
```
Alternatively, add the following snippet to your `.bashrc` (or variant):
```shell
# >> replik (start)
replik(){
    CURDIR=$PWD
    REPDIR=$HOME/.replik
    cd $REPDIR && python -m replik.replik $CURDIR $@
    cd $CURDIR
}
# << replik (end)
```

To update to the latest version you simply have to `git pull` to the latest version.


#### Multi-User setup
If you install this for multiple users don't forget to ```umask 0022```:
```
git clone git@github.com:jutanke/replik.git ~/.replik
cd ~/.replik
umask 0022
sudo pip install -r requirements.txt
```

Move the following script into ```/etc/profile.d/```
```bash
alias python=python3
replik(){
    CURDIR=$PWD
    REPDIR=/srv/replik
    if [ "$#" == 1 ]; then
        cd $REPDIR && python -m replik.replik $CURDIR $1
    elif [ "$#" == 2 ]; then
        param2=$(echo $2 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2
    fi
    cd $CURDIR
}
```
assuming replik is located in ```/srv/replik```.

## Usage
To create a new replik repository, navigate to a folder and
```
replik init
```
where you provide a project name and (optional) as many folder paths as you like.
This folders will be mapped into the container.
The current user will be mapped as docker user so files created inside the docker environment will be owned by the host user.
This process will initialize the directory with the following structure:
* `.replik` JSON file containing base informations for the project
* `docker/`
  * `Dockerfile` Base dockerfile that defines the project environment
  * `bashhook.sh` script that is called as soon as the container is entered. **This is very slow** as this is NOT cached so only add functionality here if you cannot add them in `hook_pre/post_useradd`.
  * `hook_post_useradd` Dockerfile commands that are added AFTER the user is created in the Dockerfile
  * `hook_pre_useradd` Dockerfile commands that are added BEFORE the user is created in the Dockerfile
* `{project_name}`
  * `scripts/` directory for scripts that can be called with `replik run script_name.py`
  
Alternatively, you can open a `bash` inside the container with
```
replik enter
```

The container has the following structure:
* `/home/user/{project_name}` maps the actual source code into the container
* `/home/user/docker` maps the docker folder into the container
* `/home/user/{basename(path)}` for each data path that was provided during the init process

### Adding data paths
Data can be mapped into the containers by simply editing the `paths.json` in the project root.
This file contains a list of folders which will be mapped into the container by their base name.
As of now `replik` supports either absolute paths or no path at all (a word without containing '/'). If a word is detected the path will be mapped to a folder with the same name in the project root; if this directory does not yet exist it will be created.

