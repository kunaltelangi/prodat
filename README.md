# ProDat

**ProDat** is an open source tool for managing machine learning models in production. It helps data scientists track experiments, organize workflows, and sync progress with their own cloud storage.

## Features

- **One command environment setup** (languages, frameworks, packages, etc)
- **Tracking and logging** for model config and results
- **Project versioning** (model state tracking)
- **Experiment reproducibility** (re-run tasks)
- **Visualize + export** experiment history
- **(coming soon) Dashboards** to visualize experiments


| Feature  | Commands|
| ------------- | ---------------------------- |
| Initializing a Project | `$ prodat init` |
| Setup a new environment | `$ prodat environment setup` |
| Run an experiment | `$ prodat run "python filename.py"` |
| Reproduce a previous experiment | `$ prodat ls` (Find the desired ID) <br> `$ prodat rerun EXPERIMENT_ID` |
| Open a workspace |   `$ prodat notebook`  (Jupyter Notebook) <br> `$ prodat jupyterlab` (JupyterLab) <br> `$ prodat rstudio` (RStudio) <br> `$ prodat terminal` (Terminal)|
| Record your project state <br> (Files, code, env, config, stats) |   `$ prodat snapshot create -m "My first snapshot!"` |
| Switch to a previous project state | `$ prodat snapshot ls` (Find the desired ID) <br> `$ prodat snapshot checkout SNAPSHOT_ID` |
| Visualize project entities | `$ prodat ls` (Experiments) <br> `$ prodat snapshot ls` (Snapshots) <br> `$ prodat environment ls` (Environments) |

### Experiment Running and Tracking

Here's a comparison of a typical logistic regression model with one leveraging prodat.

<table class="tg">
  <tr>
    <th class="tg-us36">Normal Script</th>
    <th class="tg-us36">With prodat</th>
  </tr>
<tr>
<td class="tg-us36">
<pre lang="python">
# train.py
#
from sklearn import datasets
from sklearn import linear_model as lm
from sklearn import model_selection as ms
from sklearn import externals as ex
#
#
#
#
#
#
iris_dataset = datasets.load_iris()
X = iris_dataset.data
y = iris_dataset.target
data = ms.train_test_split(X, y)
X_train, X_test, y_train, y_test = data
#
model = lm.LogisticRegression(solver="newton-cg")
model.fit(X_train, y_train)
ex.joblib.dump(model, 'model.pkl')
#
train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test)
#
print(train_acc)
print(test_acc)
#
#
#
#
#
#
#
#
#
</pre></td>
<td class="tg-us36">
<pre lang="python">
# train.py
#
from sklearn import datasets
from sklearn import linear_model as lm
from sklearn import model_selection as ms
from sklearn import externals as ex
import prodat # extra line
#
config = {
    "solver": "newton-cg"
} # extra line
#
iris_dataset = datasets.load_iris()
X = iris_dataset.data
y = iris_dataset.target
data = ms.train_test_split(X, y)
X_train, X_test, y_train, y_test = data
#
model = lm.LogisticRegression(**config)
model.fit(X_train, y_train)
ex.joblib.dump(model, "model.pkl")
#
train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test)
#
stats = {
    "train_accuracy": train_acc,
    "test_accuracy": test_acc
} # extra line
#
prodat.snapshot.create(
    message="my first snapshot",
    filepaths=["model.pkl"],
    config=config,
    stats=stats
) # extra line
</pre></td>
</tr>
</table>

In order to run the above code you can do the following. 

1. Navigate to a directory with a project

        $ mkdir MY_PROJECT
        $ cd MY_PROJECT

2. Initialize a prodat project

        $ prodat init
       
3. Copy the prodat code above into a `train.py` file in your `MY_PROJECT` directory
4. Run the script like you normally would in python 

        $ python train.py
        
5. Congrats! You just created your first snapshot :) Now run an ls command for snapshots to see your first snapshot.

        $ prodat snapshot ls
        

## How it works
### Project Structure
When running `prodat init`, prodat adds a hidden `.prodat` directory which keeps track of all of the various entities at play. This is ncessary to render a repository prodat-enabled. 

## Transform a Current Project
You can transform your existing repository into a prodat enabled repository with the following command
```
$ prodat init
```
If at any point you would like to remove prodat you can just remove the `.prodat` directory from your repository
or you can run the following command
```
$ prodat cleanup
```

## Sharing (Workaround)
**DISCLAIMER:** This is not currently an officially supported option and only works for 
file-based storage layers (as set in the configuration) as a workaround to share prodat projects. 

Although prodat is made to track changes locally, you can share a project by pushing to a remote 
server by doing the following (this is shown only for git, if you are using another SCM 
tracking tool, you can likely do something similar). If your files are too big or 
cannot be added to SCM then this may not work for you. 

The below has been tested on BASH terminals only. If you are using another terminal, you 
may run into some errors. 

### Push to remote
```
$ git add -f .prodat/*  # add in .prodat to your scm
$ git commit -m "adding .prodat to tracking"  # commit it to your scm
$ git push  # push to remote
$ git push origin +refs/prodat/*:refs/prodat/*  # push prodat refs to remote
```
The above will allow you to share prodat results and entities with yourself or others on 
other machines. NOTE: you will have to remove .prodat/ from tracking to start using prodat
on the other machine or another location. See the instructions below to see how to replicate
it at another location

### Pull from remote
```
$ git clone YOUR_REMOTE_URL
$ cd YOUR_REPO 
$ echo '.prodat/*' > .git/info/exclude  # include .prodat into your .git exclude
$ git rm -r --cached .prodat  # remove cached versions of .prodat from scm
$ git commit -m "removed .prodat from tracking"  # clean up your scm so prodat can work 
$ git pull origin +refs/prodat/*:refs/prodat/*  # pull prodat refs from remote
$ prodat init  # This enables prodat in the new location. If you enter blanks, no project information will be updated
```

## Running Tests

prodat uses pytest for testing. To run the full test suite:

```
$ python -m pytest
```

### Running Tests Without Docker

Some tests require a running Docker daemon. If you don't have Docker installed or running, you can skip these tests by setting the `prodat_SKIP_DOCKER_TESTS` environment variable:

```
$ prodat_SKIP_DOCKER_TESTS=1 python -m pytest
```

This will skip all tests that depend on Docker, allowing the test suite to run successfully without a Docker environment.

# FAQs

Q: What  do I do if the `prodat stop --all` doesn't work and I cannot start a new container due to port reallocation?  
A: This could be caused by a ghost container running from another prodat project or another container.  Either you can create a docker image with a specific port allocation (other than 8888),  find the docker image, stop it, and remove it using `docker ps --all` and `docker conntainer stop <ID>` and `docker container rm <ID>`. Or you can stop and remove all images running on the machine [NOTE: This may  affect other docker processes on  your machine so PROCEED WITH CAUTION] `docker container stop $(docker ps  -a -q)` and `docker container rm $(docker ps  -a -q)`
