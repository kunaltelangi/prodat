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
