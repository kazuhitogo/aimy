#!/usr/bin/env bash
# Compare aimy (checked / --fast) against CPython.
set -e
cd "$(dirname "$0")/.."
A=.venv/bin/aimy
t() { local s=$(date +%s.%N); "$@" >/dev/null; echo "$(date +%s.%N) - $s" | bc; }
for spec in "fib 32" "sieve 20000000" "nbody 2000000"; do
  set -- $spec
  $A build examples/$1.aim -o /tmp/aim_$1 >/dev/null
  $A build examples/$1.aim -o /tmp/aim_$1_fast --fast >/dev/null
  printf "%-8s aimy=%6.2fs  aimy--fast=%6.2fs  python=%6.2fs\n" $1 \
    $(t /tmp/aim_$1 $2) $(t /tmp/aim_$1_fast $2) $(t python3 bench/$1.py $2)
done
