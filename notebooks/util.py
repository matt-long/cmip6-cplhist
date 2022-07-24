import os
from subprocess import check_call, check_output, STDOUT
import tempfile

import dask
from dask_jobqueue import PBSCluster
from dask.distributed import Client

USER = os.environ['USER']
try:
    TMPDIR = os.environ['TMPDIR']
except KeyError:   
    print('TMPDIR not set; set TMPDIR environment variable')
    raise

path_to_here = os.path.dirname(os.path.realpath(__file__))

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
        resource_spec=f'select=1:ncpus=1:mem={memory}',
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


def extract_tar_pbs(tarfile, dirout, project='NCGD0011'):
    job_script = [
        '#!/bin/csh',
        f'#PBS -N untar',
        f'#PBS -A {project}',
        '#PBS -l select=1:ncpus=1:mem=20GB',
        '#PBS -l walltime=01:00:00',
        '#PBS -q casper',
        f'#PBS -o ${TMPDIR}/',
        f'#PBS -e ${TMPDIR}/',
        '',
        f'cd {dirout}',
        f'tar -xvf {tarfile}',
    ]    
    _, script_name = tempfile.mkstemp(dir=TMPDIR, prefix='untar.')
    with open(script_name, 'w') as fid:
        for line in job_script:
            fid.write(f'{line}\n')
    return check_output(['qsub', script_name]).decode("UTF-8").strip().split('.')[0]
    


    
def concat_cplhist_mon(case, stream, yr_lo, yr_hi, project='NCGD0011'):
    """
    concatenate daily CPLHIST files to monthly to conform to data model
    expectations.
    """
    exe = f'{path_to_here}/./concat_cpl_hist_mon.csh'
    dir_daily = f'{cplhist_stage_root}/cpl_hist/{case}/orig'
    year0 = f'{yr_lo:04d}'
    year1 = f'{yr_hi:04d}'
    dir_monthly = f'{cplhist_stage_root}/cpl_hist/{case}/monthly'
    
    job_script = [
        '#!/bin/csh',
        f'#PBS -N concat-cplhist.{case}.{stream}.{yr_lo}-{yr_hi}',
        f'#PBS -A {project}',
        '#PBS -l select=1:ncpus=1:mem=20GB',
        '#PBS -l walltime=12:00:00',
        '#PBS -q casper',
        f'#PBS -o /glade/scratch/{USER}/',
        f'#PBS -e /glade/scratch/{USER}/',
        '',
        f'{exe} {case} {dir_daily} {year0} {year1} {dir_monthly} {stream}'
    ]
    _, script_name = tempfile.mkstemp(dir=TMPDIR, prefix='concat-cplhist.')
    with open(script_name, 'w') as fid:
        for line in job_script:
            fid.write(f'{line}\n')

    return check_output(['qsub', script_name]).decode("UTF-8").strip().split('.')[0]
