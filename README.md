# CESM ocean-ice integrations using CMIP6 coupler history-file output

This repository contains utilities to support running ocean-ice integrations using output from the CESM coupler generated during the fully coupled CMIP6 integrations.

## Procedure

1. Specify the CMIP6 coupled cases to replicate in [cplhist-cases.yml](./notebooks/cplhist-cases.yml).

1. Stage `cpl_hist` output and restart files:
   Run the [stage-cplhist-and-restarts.ipynb](./notebooks/stage-cplhist-and-restarts.ipynb)
   notebook, which access the `cpl_hist` tar files from /glade/campaign as well as the restart
   files from the parent cases.
   
1. Stage surface salinity data: 
   Run the [stage-restoring-data.ipynb](./notebooks/stage-restoring-data.ipynb) notebook. 
   This concatenates and subsets surface salinity data from the original coupled integrations.
