ZSH=$HOME/.zshrc
BRC=$HOME/.bashrc

if [ -f "$ZSH" ]; then
    RC=$ZSH
elif [ -f "$BRC" ]; then
    RC=$BRC
else
    echo "No .bashrc found... exiting"
    exit 1
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

COMMAND="python $DIR/replik/replik.py"

echo " " >> $RC
echo "# >> replik (start)" >> $RC
echo "replik(){" >> $RC
echo '    CURDIR=$PWD' >> $RC
echo "    REPDIR=$DIR" >> $RC
echo '    if [ "$#" == 1 ]; then' >> $RC
echo '        cd $REPDIR && python -m replik.replik $CURDIR $1' >> $RC
echo '    elif [ "$#" == 2 ]; then' >> $RC
echo "        param2=$(echo $2 | tr ' ' '#')" >> $RC
echo "        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2" >> $RC
echo '    elif [ "$#" == 3 ]; then' >> $RC
echo "        param2=$(echo $2 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $3 | tr ' ' '#')" >> $RC
echo "        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3" >> $RC
echo '    elif [ "$#" == 4 ]; then' >> $RC
echo "        param2=$(echo $2 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $3 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $4 | tr ' ' '#')" >> $RC
echo "        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3 $param4" >> $RC
echo '    elif [ "$#" == 5 ]; then' >> $RC
echo "        param2=$(echo $2 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $3 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $4 | tr ' ' '#')" >> $RC
echo "        param3=$(echo $5 | tr ' ' '#')" >> $RC
echo "        cd $REPDIR && python -m replik.replik $CURDIR $1 $param2 $param3 $param4 $param5" >> $RC
echo "    fi" >> $RC
echo '    cd $CURDIR' >> $RC
echo "}" >> $RC
echo "# << replik (end)" >> $RC
