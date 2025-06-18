#!/bin/bash
if [ ${#VIRTUAL_ENV} -gt 0 ]; then
    deactivate
fi

check_process_id() {
  if [ "$(uname)" == "Darwin" ]; then
    # tips
    echo -e "\033[34m ps -ef |grep \"$1\" |grep -v \"grep\" |awk '{print \$2}' |head -n 1 \033[0m"
    pid=`ps -ef |grep "$1" |grep -v "grep" |awk '{print $2}' |head -n 1`
  else
    # tips
    echo -e "\033[34m ps -aux |grep \"$1\" |grep -v \"grep\" |awk '{print \$2}' |head -n 1 \033[0m"
    pid=`ps -aux |grep "$1" |grep -v "grep" |awk '{print $2}' |head -n 1`
  fi
  # echo "process: $1 / pid: $pid"
  if [ -z $pid ]; then
    pid=0
  fi
}
check_port() {
  if [ "$(uname)" == "Darwin" ]; then
    # tips
    echo -e "\033[34m netstat -anp tcp -v | grep \".$1 \" |awk '{print \$11}' |head -n 1 \033[0m"
    temp=`netstat -anp tcp -v | grep ".$1 " |awk '{print $11}' |head -n 1`
    pid=${temp%/*}
  else
    # tips
    echo -e "\033[34m netstat -tlpn | grep \":$1 \" |grep -v \"grep\" |awk '{print \$7}' |head -n 1 \033[0m"
    temp=`netstat -tlpn | grep ":$1 " |grep -v "grep" |awk '{print $7}' |head -n 1`
    pid=${temp%/*}
  fi
  # echo "port: $1 / pid: $pid"
  if [ -z $pid ]; then
    pid=0
  fi
}

if [ -f '.env' ]; then
  source .env
elif [ -f '.env.sample' ]; then
  source .env.sample
else
  export UVICORN_PORT=8000
fi

ulimit -n 1048576

if [ "$1" == "init" ]; then
  if [ -d ".venv" ]; then
    echo Virtual Environment already exists
    source .venv/bin/activate
    pip install -r requirements.txt
  else
    echo Install Virtual Environment...
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
  fi
elif [ "$1" == "clear" ]; then
    rm -fr "__pycache__"
# main
elif [ "$1" == "log" ]; then ## log
    tail -f log-main.log
elif [ "$1" == "kill" ]; then ## stop
  check_port $UVICORN_PORT
  while [ $pid -gt 1 ]
  do
    # tips
    echo -e "\033[34m kill -9 $pid \033[0m"
    kill -9 $pid
    
    check_port $UVICORN_PORT
  done
  # tips
  echo -e "\033[31m 'main.py' is not exist. \033[0m"
  echo ""
elif [ "$1" == "run" ]; then ## run
  check_port $UVICORN_PORT
  if [ $pid -eq 0 ]; then
    echo Virtual Environment Activation...
    source .venv/bin/activate
    echo Launching main.py ...
    python3 main.py $2 $3 $4 $5 $6
  else
    # tips
    echo -e "\033[31m 'main.py' is exist. \033[0m"
  fi
else
  check_port $UVICORN_PORT
  if [ $pid -eq 0 ]; then
    echo Virtual Environment Activation...
    source .venv/bin/activate
    echo Launching main.py ...
    nohup python3 main.py $1 $2 $3 $4 $5 $6 > log-main.log 2>&1 &
  else
    # tips
    echo -e "\033[31m 'main.py' is exist. \033[0m"
  fi
fi
