import os

from subprocess import check_call, check_output, STDOUT

import dask
from dask_jobqueue import PBSCluster
from dask.distributed import Client

USER = os.environ['USER']
cplhist_stage_root = f'/glade/scratch/{USER}/cplhist_data'
restart_stage_root = f'{cplhist_stage_root}/restarts'
restoring_data_stage_root = f'{cplhist_stage_root}/restoring_data'


def get_ClusterClient(memory="25GB", project='NCGD0011', walltime='06:00:00'):
    """return client and cluster"""
    cluster = PBSCluster(
        cores=1,
        memory=memory,
        processes=1,
        queue='casper',
        local_directory=f'/glade/scratch/{USER}/dask-workers',
        log_directory=f'/glade/scratch/{USER}/dask-workers',
        resource_spec='select=1:ncpus=1:mem=25GB',
        project=project,
        walltime=walltime,
        interface='ib0',)

    jupyterhub_server_name = os.environ.get('JUPYTERHUB_SERVER_NAME', None)    
    dashboard_link = 'https://jupyterhub.hpc.ucar.edu/stable/user/{USER}/proxy/{port}/status'
    if jupyterhub_server_name:
        dashboard_link = (
            'https://jupyterhub.hpc.ucar.edu/stable/user/'
            + '{USER}'
            + f'/{jupyterhub_server_name}/proxy/'
            + '{port}/status'
        )
    dask.config.set({'distributed.dashboard.link': dashboard_link})
    client = Client(cluster)
    return cluster, client


def list_files_in_tar(tarfile):
    """return a list of the files in a tarball"""
    stdout = check_output(['tar', '-tf', tarfile], stderr=STDOUT)
    return stdout.decode("UTF-8").split('\n')


def extract_tar(tarfile, dirout):
    """extract tar archive to `dirout`"""
    check_call(['tar', '-xvf', tarfile], cwd=dirout)

        
def concat_cplhist_mon(case, yr_lo, yr_hi):
    """
    concatenate daily CPLHIST files to monthly to conform to data model
    expectations.
    """
    check_call([
        'csh',
        'concat_cpl_hist_mon.csh',
        case,                                             # CASE
        f'{cplhist_stage_root}/cpl_hist/{case}/orig',     # DIR_DAILY
        f'{yr_lo:04d}',                                   # YEAR0
        f'{yr_hi:04d}',                                   # YEAR1
        f'{cplhist_stage_root}/cpl_hist/{case}/monthly',  # DIR_MONTHLY
    ])
