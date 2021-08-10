# Sample project

We want to run [SPL](https://github.com/eth-ait/spl) inside a scheduable container:

**Step 1**:
Create directory and initialize replik project:
```bash
$ mkdir spl_runner
$ cd spl_runner && replik init-simple
```
A prompt will ask you to choose a name for this project. To start, we simply go with "spl_runner".

**Step 2**
Prepare the docker environment. 
To do so we open the file ```spl_runner/docker/hook_pre_useradd``` and add the following lines:
```docker
# As SPL uses rather old libraries we first need to downgrade python to 3.6.5.
RUN conda install python=3.6.5

# next we want to install the required python libraries:
RUN curl https://raw.githubusercontent.com/eth-ait/spl/master/requirements.txt -o requirements.txt && pip install -r requirements.txt
```

**Step 3**
We want to work on the source code directly so next we clone the spl project into the root folder ```spl_runner```:
```
cd spl_runner && git clone https://github.com/eth-ait/spl.git
```
If we want to place this project under version control we have to remove the underlying git repository first:
```
rm -rf spl_runner/spl/.git
```


