replik(){
    CURDIR=$PWD
    REPDIR=/srv/replik
    if [ "$#" == 1 ]; then
        cd $REPDIR && python -m replik.replik $CURDIR $1
    elif [ "$#" == 2 ]; then
        param2=$(echo $2 | tr ' ' '#')
        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2
    fi
    cd $CURDIR
}