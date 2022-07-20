import os
import copy
from subprocess import check_output, Popen, PIPE
from collections import OrderedDict

import warnings

import numpy as np
import xarray as xr

m2_per_cm2 = 1e-4

radius_earth = 6.37122e6  # m


def ncks_fl_fmt64bit(file_in, file_out=None):
    """
    Converts file to netCDF-3 64bit by calling:
      ncks --fl_fmt=64bit  file_in file_out

    Parameter
    ---------
    file : str
      The file to convert.
    """

    if file_out is None:
        file_out = file_in

    ncks_cmd = " ".join(["ncks", "-O", "--fl_fmt=64bit_offset", file_in, file_out])
    cmd = " && ".join(["module load nco", ncks_cmd])

    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)

    stdout, stderr = p.communicate()
    if p.returncode != 0:
        print(stdout.decode("UTF-8"))
        print(stderr.decode("UTF-8"))
        raise


def to_netcdf_clean(dset, path, netcdf3=True, **kwargs):
    """wrap to_netcdf method to circumvent some xarray shortcomings"""

    import sys
    from netCDF4 import default_fillvals

    dset = dset.copy()

    # ensure _FillValues are not added to coordinates
    for v in dset.coords:
        dset[v].encoding["_FillValue"] = None

    for v in dset.data_vars:

        # if dtype has been set explicitly in encoding, obey
        if "dtype" in dset[v].encoding:
            if dset[v].encoding["dtype"] == np.float64:
                dset[v].encoding["_FillValue"] = default_fillvals["f8"]
            elif dset[v].encoding["dtype"] == np.float32:
                dset[v].encoding["_FillValue"] = default_fillvals["f4"]
            elif dset[v].encoding["dtype"] in [np.int32]:
                dset[v].encoding["_FillValue"] = default_fillvals["i4"]

        # otherwise, default to single precision output
        elif dset[v].dtype in [np.float32, np.float64]:
            dset[v].encoding["_FillValue"] = default_fillvals["f4"]
            dset[v].encoding["dtype"] = np.float32

        elif dset[v].dtype in [np.int32, np.int64]:
            dset[v].encoding["_FillValue"] = default_fillvals["i4"]
            dset[v].encoding["dtype"] = np.int32
        elif dset[v].dtype == object:
            pass
        else:
            warnings.warn(f"warning: unrecognized dtype for {v}: {dset[v].dtype}")

        if "_FillValue" not in dset[v].encoding:
            dset[v].encoding["_FillValue"] = None

    sys.stderr.flush()

    print("-" * 30)
    print(f"Writing {path}")
    dset.to_netcdf(path, **kwargs)
    print("")
    if netcdf3:
        ncks_fl_fmt64bit(path)

    dumps = check_output(["ncdump", "-h", path]).strip().decode("utf-8")
    print(dumps)
    dumps = check_output(["ncdump", "-k", path]).strip().decode("utf-8")
    print(f"format: {dumps}")
    print("-" * 30)


def code_checkout(remote, coderoot, tag):
    """Checkout code for CESM
    If sandbox exists, check that the right tag has been checked-out.

    Otherwise, download the code, checkout the tag and run manage_externals.
    """

    sandbox = os.path.join(coderoot, tag)

    if os.path.exists(sandbox):
        print(f"Check for right tag: {sandbox}")
        p = Popen("git status", shell=True, cwd=sandbox, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        stdout = stdout.decode("UTF-8")
        stderr = stderr.decode("UTF-8")
        print(stdout)
        print(stderr)
        if tag not in stdout.split("\n")[0]:
            raise ValueError("tag does not match")

    else:
        if not os.path.exists(coderoot):
            os.makedirs(coderoot)

        # clone the repo
        p = Popen(
            f"git clone {remote} {tag}",
            shell=True,
            cwd=coderoot,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = p.communicate()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        if p.returncode != 0:
            raise Exception("git error")

        # check out the right tag
        assert os.path.exists(sandbox)
        p = Popen(f"git checkout {tag}", shell=True, cwd=sandbox)
        stdout, stderr = p.communicate()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        if p.returncode != 0:
            raise Exception("git error")

        # check out externals
        p = Popen("./manage_externals/checkout_externals -v", shell=True, cwd=sandbox)
        stdout, stderr = p.communicate()
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        if p.returncode != 0:
            raise Exception("git error")

    return sandbox


def dim_cnt_check(ds, varname, dim_cnt):
    """confirm that varname in ds has dim_cnt dimensions"""
    if len(ds[varname].dims) != dim_cnt:
        raise ValueError(
            f"unexpected dim_cnt={len(ds[varname].dims)}, varname={varname}"
        )


def get_area(ds, component):
    """return area DataArray appropriate for component"""
    if component == "ocn":
        dim_cnt_check(ds, "TAREA", 2)
        return ds["TAREA"]
    if component == "ice":
        dim_cnt_check(ds, "tarea", 2)
        return ds["tarea"]
    if component == "lnd":
        dim_cnt_check(ds, "landfrac", 2)
        dim_cnt_check(ds, "area", 2)
        da_ret = ds["landfrac"] * ds["area"]
        da_ret.name = "area"
        da_ret.attrs["units"] = ds["area"].attrs["units"]
        return da_ret
    if component == "atm":
        dim_cnt_check(ds, "gw", 1)
        area_earth = 4.0 * np.pi * radius_earth ** 2  # area of earth in CIME [m2]

        # normalize area so that sum over "lat", "lon" yields area_earth
        area = ds["gw"] + 0.0 * ds["lon"]  # add "lon" dimension
        area = (area_earth / area.sum(dim=("lat", "lon"))) * area
        area.attrs["units"] = "m2"
        return area
    msg = f"unknown component={component}"
    raise ValueError(msg)


def gen_time_components_variable(time, year_offset=0.):

    if isinstance(time, xr.DataArray):
        time_data = time.values
    else:
        time_data = time

    tc = xr.DataArray(
        [(d.year + year_offset, d.month, d.day, d.hour, d.minute, d.second) for d in time_data],
        dims=('time', 'n_time_components'),
        coords={'time': time},
        attrs={'long_name': 'time components (year, month, day, hour, min, sec)', 'units': 'none'},
        name='time_components',
    )
    tc.encoding['_FillValue'] = None
    tc.encoding['dtype'] = np.int32
    return tc