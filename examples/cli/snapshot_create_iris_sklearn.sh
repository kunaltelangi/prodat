#!/usr/bin/env bash

# This script will create a prodat-enabled repository in the current directory
# run the initial script to create a snapshot and will list out the snapshots
# by calling the `prodat snapshot ls` command

# Create a prodat-enabled repo
prodat init --name="iris data with sklearn models" --description="use iris data along with sklearn models"

# Run the script to create a snapshot
python snapshot_create_iris_sklearn.py

# Run the prodat command to list all snapshots
prodat snapshot ls