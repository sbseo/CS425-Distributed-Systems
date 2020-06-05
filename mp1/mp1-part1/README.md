# MP1

We deign an asynchronous banking system in this MP.
Each process will keep a list of all the bank accounts and the amounts in their bank accounts.
A process "X" may DEPOSIT or TRANSFER money between accounts.
Process "X" then must notify all other processes of this event in order for them to update their state.

The main goal is to achieve a total ordering of all the events in each process such that they all match the true global clock's timeline.

## Folders

* spec: Contains a Maude specification verified with linear temporal logic
* results: Contains log files after the exeriment
* python: This contains a Python implementation of the code

## How to run program

    python3 -u gentx.py 0.5 | python3 main.py <N> <O>
  
At each virtual machine, please run the code above where N is number of total nodes and O is number of vm offset. <br>
For example, suppose you are unning VM number 3 (out of 8). <br>
Then the program can be run by the following command:
  
    python3 -u gentx.py 0.5 | python3 main.py 8 3

To finish the program, please click ctrl + c. This will create a log file which shows the results of an experiment. Log file includes total ordering verfication, final balance, bandwidth for each second, and timestamps when each transaction is processed


## Dependencies

Please install apscheduler by

    pip install APScheduler

## Last things to do

1. Graph visualization per each scenario (Bruno)
2. Report 
3. Implement CRASH scenario