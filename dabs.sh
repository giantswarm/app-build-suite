#!/bin/sh

docker run -it --rm -v `pwd`:/abs/workdir/ abs:test $@
