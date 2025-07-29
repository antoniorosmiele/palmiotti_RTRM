# Scripts for plotting the incident matrix

This script is very confusing, as it was made for analysis purposes and not meant to be reused, I apologize... It is highly suggested to refactor these scripts.

### Data

In the data folder you will find the data related to GPU-GPU, GPU-DLA, DLA-GPU, DLA-DLA executions. Only the CSVs are relevant to the functioning of the script, however more accurate logs are also available.

In order to recreate this plots, you will need to structure the folders in the following way:
- Each log folder will contain subfolders that hold the different combinations of coexecution. For example
    - logsA: contains matching pairs (model1 with model1, model2 with model2 ... modelK with modelK)
    - logsB: contains pairs offset by 1 (model1 with model2, model2 with model3 ... modelK with model1)
    - logsC: contains pairs offset by 2 ...
    - logsZ: contains standalone execution

For each of these log folders you will have to folders for the two models taken into consideration. For example in logsB you will have:
- logs1
    - model1, model2, model3 ... modelK
- logs2
    - model2, model3, model4 ... model1

Do not that only the csvs are relevant in this folder.

In case you want to consider the coexecution of more than 2 models, since we're only able to plot a 2D matrix, it suffices to run 3 benchmark scripts alongside each other and then extract only informations regarding 2 dimensions (aka, 2 of the 3 running processes) in order to get the desired "slice"

### Scripts

Each plot_incident_XX.py script was created with the idea of plotting a different interference matrix. Because of this, 4 different scripts are made in order to allow easier changes to how the different plots look (since all matrices differ in size). However, most of the scripts logic is overlapped. It is suggested to use these script to simply create the interference matrices (which you will find in /out).

plot_matrix.py is the script used to plot all matrices together as was done in the paper.