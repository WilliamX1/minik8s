#!/bin/bash


expect -c "
    spawn rsync --archive --partial --progress stu639@data.hpc.sjtu.edu.cn:/lustre/home/acct-stu/stu639/data/ /data/
    expect {
        \"yes/no\" {send \"yes\r\";exp_continue;}
        \"*Password\" {set timeout 500;send \"7E4uZ%XY\r\";}
    }
expect eof"