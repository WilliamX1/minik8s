#!/bin/bash

modulename=$1

expect -c "
    spawn scp -r /data/ stu639@data.hpc.sjtu.edu.cn:/lustre/home/acct-stu/stu639/
    expect {
        \"yes/no\" {send \"yes\r\";exp_continue;}
        \"*Password\" {set timeout 500;send \"7E4uZ%XY\r\";}
    }
expect eof"


expect -c "
    spawn ssh stu639@login.hpc.sjtu.edu.cn
    expect {
        \"yes/no\" {send \"yes\r\";exp_continue;}
        \"*Password\" {set timeout 500;send \"7E4uZ%XY\r\";}
    }
    expect \"stu639@*\" {send \"module load gcc/8.3.0 cuda/10.1.243-gcc-8.3.0\r\"}
    expect \"stu639@*\" {send \"cd data\r\"}
    expect \"stu639@*\" {set timeout 500;send \"nvcc $modulename.cu -o $modulename -lcublas\r\"}
    expect \"stu639@*\" {set timeout 500;send \"sbatch $modulename.slurm\r\"}
    expect \"stu639@*\" {set timeout 500;send \" exit\r\"}

expect eof"

#expect -c "spawn module load gcc/8.3.0 cuda/10.1.243-gcc-8.3.0"