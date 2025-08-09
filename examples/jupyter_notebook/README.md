# CLI + Jupyter Notebook Flow Examples

In order to run the examples, make sure that you have prodat properly installed with the latest 
stable or development version. You can install it with the following command:
```
$ pip install prodat
```

## Using the Examples
### Setup
1. Navigate to desired project folder or create a new one 

        $ mkdir MY_prodat_PROJECT
        $ cd MY_prodat_PROJECT
        
2. Initialize the prodat project

        $ prodat init

3. Copy/save example files within project folder (if directory, copy the contents of the directory)

        $ cp /path/to/DIRECTORY/* .
        
4. Follow the instructions for a given example in the table below


### Examples

| feature  | filename(s) | Instructions |
| ------------- |:-------------:| -----|
| Create Snapshot | `snapshot_create_iris_sklearn.ipynb`| (1) Run `$ jupyter notebook snapshot_create_iris_sklearn.ipynb` <br>(2) Run cells in order |
| Opening a new Jupyter Notebook workspace | N/A | (1) `$ prodat environment setup`, choose any image containing python <br> (2) Run `$ prodat notebook`  |