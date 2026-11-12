#!/bin/bash

# Setup extension
echo "[ckan-test.run-tests] Database init"
ckan -c test.ini db init

echo "[ckan-test.run-tests] Database pending migrations"
ckan -c test.ini db pending-migrations --apply

# Default test directory and output file
TEST_DIR="tests"

# Parse options
while getopts 'cd:o:' OPTION; do
  case "$OPTION" in
    c)
        RUN_COVERALLS=1;;
    d)
        TEST_DIR="$OPTARG";;
    ?)
        RUN_COVERALLS=0;
        exit 1;;
  esac
done
shift "$(($OPTIND -1))"

if [ -n "$1" ]; then
    echo "[ckan-test.run-tests] pytest --ckan-ini=test.ini --cov=\"$1\" --cov-report=term-missing --cov-append --disable-warnings $TEST_DIR"
    pytest --ckan-ini=test.ini --cov="$1" --cov-report=term-missing --cov-append --disable-warnings "$TEST_DIR"
    test_exit_code=$?
else
    echo "[ckan-test.run-tests] pytest --ckan-ini=test.ini --cov-report=term-missing --cov-append --disable-warnings $TEST_DIR"
    pytest --ckan-ini=test.ini --cov-report=term-missing --cov-append --disable-warnings "$TEST_DIR"
    test_exit_code=$?
fi

if [ "$RUN_COVERALLS" = 1 ]; then
    coveralls;
fi

exit $test_exit_code