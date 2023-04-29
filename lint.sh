#! /bin/sh

if [ -z "$1" ]
then
	for f in scripts/firewater firewater/*.py
	do
		PYTHONPATH=$(pwd) pylint --rcfile ./pylintrc $f
		MYPYPATH=$(pwd) mypy $f
		flake8 $f
	done
else
	PYTHONPATH=$(pwd) pylint --rcfile ./pylintrc "$@"
	MYPYPATH=$(pwd) mypy "$@"
	flake8 "$@"
fi

