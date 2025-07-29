# Plotting experimental results

These scripts are used to plot the experimental results as presented in the paper.

### Data

In the ./data folder, you will find 10 configurations (workloads) as performed by the 4 different strategies. Note that:
- dumb+schedutil is Naive + OS Governor
- policy+refine is Policy

### Scripts

If you want to add a configuration, you must first collect the proper csvs as presented in the example files. You can use the policy scripts as benchmark to get the deisred csvs. However, if you do so, make sure to run util.py beforehand, to add the necessary "label" column for the scripts to work.