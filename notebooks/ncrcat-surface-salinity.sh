#!/bin/bash

set -e

FILE_LIST=${1}
FILE_OUT=${2}
VARNAME=${3}

module load nco

# concatenate files
ncrcat -O -d z_t,0 -v ${VARNAME},TLAT,TLONG,time,time_bound \
  -o ${FILE_OUT} ${FILE_LIST}
  
# change file format  
ncks -O --fl_fmt=64bit_offset ${FILE_OUT} ${FILE_OUT}


if [ ${VARNAME} == "SSS" ]; then
    # rename to SALT
    ncrename -O -v ${VARNAME},SALT ${FILE_OUT}

    # center time
    ncap2 -O -s "time=time-0.5" ${FILE_OUT} ${FILE_OUT}

else # assume monthly
    # eliminate degenerate dimension
    ncwa -O -a z_t ${FILE_OUT} ${FILE_OUT}

fi

