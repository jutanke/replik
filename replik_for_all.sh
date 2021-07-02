alias python=python3
replik(){
    CURDIR=$PWD
    REPDIR=/srv/replik
    if [ "$#" == 1 ]; then
        cd $REPDIR && python -m replik.replik $CURDIR $1
    elif [ "$#" == 2 ]; then
        param2=$(echo $2 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2
    elif [ "$#" == 3 ]; then
        param2=$(echo $2 | tr ' ' '#')
        param3=$(echo $3 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3
    elif [ "$#" == 4 ]; then
        param2=$(echo $2 | tr ' ' '#')
        param3=$(echo $3 | tr ' ' '#')
        param4=$(echo $4 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3 $param4
    elif [ "$#" == 5 ]; then
        param2=$(echo $2 | tr ' ' '#')
        param3=$(echo $3 | tr ' ' '#')
        param4=$(echo $4 | tr ' ' '#')
        param5=$(echo $5 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3 $param4 $param5
    fi
    cd $CURDIR
}