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
echo '    cd $REPDIR && python -m replik.replik $CURDIR $@' >> $RC
echo '    cd $CURDIR' >> $RC
echo "}" >> $RC
echo "# << replik (end)" >> $RC