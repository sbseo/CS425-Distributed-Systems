# Maude Specification

This is the Maude specification that we will be using for model checking our protocol.
Once this has been verified using LTL this will be converted into a Python implementation.

## Key Assumptions

* This specification assumes that the underlying transmission protocol is reliable.
* As this is a specification we have global variables such as a global message counter that is accessible to all nodes.  This is used to generate unique message IDs.  This cannot be used in a real implemenation.
* We do not implement the application level updates of the accounts.
This is irrelevant to modeling a total ordering of messages.
We only need to ensure messages are delivered in order.
From there on, the actual content of the messages is irrelevant and can be handled in the acutal implementation.

## TODOs

* State is incomplete
	* Rewrite rules
	* In the "repmsg" rule, does the sender send RRep back to itself?
	Or do we do this in the SSend rule

## Files

* Support.maude: This contains all supporting modules that will be used
* Account.maude: The specification for the accounts
* Message.maude: The specification for the messages
* Process.maude: The specification for the processes
* State.maude: The specification for the state of the distributed system
* spec.maude: Unused for now
* Test.maude: Test cases for modules

## Data Structures

### Accounts

Accounts have the following form

	op A[_|_] : AccId Balance -> Acc [ctor] .

Therefore the account below has ID 15 and a balance of 20 dollars.

	A[15 | 20]

### Messages

The protocol uses two different messages.
Namely there are replies to new messages being sent and the messages themseles.
Messages have the following form.

	--- Parameters
	--- 	Nat: Actual total ordering number
	--- 	Nat: Source of a transfer (used only in transfer)
	--- 	Nat: Seq num we assign
	--- 	Nat: Have we assigned a seq num if yes else 0
	op M[_|_|_|_] : Nat Nat Nat Nat -> Msg [ctor] .


Therefore to represent an event initiated from process 15 and is the totally ordered 5th message we have.

	M[5 | 15 | 0 | 0]

The third and the fourth parameter are used by receivers in the holdback queue.
More specifically, the third parameter the sequence number is used for ordering items before we push them to the appplication.

To represent the replies that a recieving process must send to determine the correct agreed sequence number is as follows.
The sequence number sent here is max2(accepted, proposed number) + 1.

	--- Parameters
	--- 	Nat: The message id this specific reply is for
	--- 	Nat: Sequence number
	--- 	Nat: This is the process identifier as multiple
	--- 		processes may send the same number
	op R[_|_|_] : Nat Nat Nat -> RRep [ctor] .

Therefore a message that a process 2 recieves from 1 with a propoesed sequence number of 500 for message id 100 is as follows...

	R[100 | 500 | 1]

Finally we have the message that the original sender of a message must multicast back to all receivers

	--- Parameters
	--- 	Nat: The message id this specific reply is for
	--- 	Nat: Largest sequence number chosen from all the RRep
	op S[_|_|_] : Nat Nat Nat -> SRep [ctor] .

Therefore if we have a message id 5 that a process 10 sent and after collecting all proposed sequence numbers the max seq number is 550 then the sender must multicast...

	S[5 | 550]

### Process

The process is described as follows.
It is composed the following parts.

	--- Parameters
	--- 	Pid: Process ID
	--- 	Nat: Largest agreed sequence number
	--- 	Nat: Proposed sequence number
	--- 	Nat: 0 if proposed seq number has not yet been assigned 1 o/w
	--- 	TOMsgList: This represents all delivered messages
	--- 	MsgList: This represents the holdback Queue, which can contain both replies from receivers, and messages to deliver to the application
	op P[_|_|_|_|_|_] : Nat Nat Nat Nat TOMsgList MsgList -> Proc [ctor] .

Therefore we have the following for a process 1, largest agreed seq 2, proposed sequence number 5, empty delivered list, and a holdback queue of one reply to a message it sent out.

	P[1 | 2 | 5 | 1 | TOMnil | M[0 | 1 | 0 | 0] :M: R[100 | 500 | 1]]

The fourth field is used to represent whether we have initialized a random proposed sequence number at startup or not.
This is not a field we need in the actual python implementation.
However we need this in our specification here to use the random number generator correctly.

### State

The state of our distributed system is shown as follows

	--- Parameters
	--- 	Nat: Counter used for generating rand (ignore in Python)
	--- 	Nat: Finished assigning random props then 1 else 0 (ignore in Python)
	--- 	Nat: Global Message ID used to generate a unique
	--- 		ID for the next message generated
	--- 	TOMsgList: Global Message List for use of comparison for total ordering
	--- 	ProcList: The list of all our processes in the system
	--- 	GMsgList: This is the "soup" representing all the channels
	--- 		all messages sent M/R will be placed here until a process acts on it
	op < cnt: _| r: _|_|_|_|_> : Nat Nat Nat TOMsgList ProcList GMsgList -> State [ctor] .
	--- This pauses our distributed system
	op [cnt: _| r: _|_|_|_|_] : Nat Nat Nat TOMsgList ProcList GMsgList -> Stop [ctor] .


* The global message ID natural number can be generated by a hash generator in Python as there is very low chance of collision.
* TOMsgList is used as a global variable used to compare with each process's delivered list.
* ProcList is a list of all our processes P[...].
* GMsgList is a list of all the messages that have been sent.
* We do not need to represent any form of channel here as we can have each process choose a message just by non-deterministically pulling it out and checking parameters of the message to determine if it is guaranteed for it.
Obviously we can not use this abstraction in Python but it is a useful one for modeling.

For example to represent a system at startup for 3 processes we have the following operator and equation.

	--- Initial state for 3 nodes, used for testing
	op init3 : -> State .
	eq init3 = 
		< 
			cnt: 0 | 
			r: 0 | 
			0 | 
			TOMnil | 
			P[0 | 0 | 0 | 0 | TOMnil | Mnil] :PP: 
				P[1 | 0 | 0 | 0 | TOMnil | Mnil] :PP:
				P[2 | 0 | 0 | 0 | TOMnil | Mnil] | 
			GMnil
		> .

To describe the possible operations each process that can occur the rewrite rules are described as follows.

0. Before we run, we must initialize all processes with its own
proposed sequence number

1. Process puts message in soup [DONE]
	NOTE: We do not care about whether we create a new account
	in this model.  This should be handled by the process itself
	and we only need to model the message creation and message ordering.

2. Process replies to a new message with proposed sequence number [IN_PROGRESS]
	* Maybe need to also include checks to not duplicate adding messages to holdback and spamming the Soup with replies.

3. Sender process collects replies from all other processes and choose the largest one. Then the sender multicasts that number back.

4. Process needs to update its sequence number list 
5. Process places a message in its holdback queue
6. Process delivers a message to the application

7. Process crashes [DONE]

8. Stop [DONE]

#### Rewrite Rules

Below some of the rewrite rules are described to help the reader understand its implementation

Let us look at the initialization process with the rule called "randprop".
The initial state occurs before the "=>" on the left.
The state after taking a step is on the right of "=>".
In this initial state note that

	r: 0 | 0

is explicitly defined.
This makes sure we only operate on cases that have these values set to 0.

The following list

	PA :PP: PLiA

pulls process PA out of our process list nondeterminitically.

On the right of the "=>" we can see that count is incrememnted by 1 and our process PA is edited with the random number to fill in our initial proposed sequence number.

	--- 0. initialize each process with a random proposed sequence number
	crl [randprop] : 
		< 
			cnt: CNT | 
			r: 0 | 
			0 | 
			TOMnil | 
			PA :PP: PLiA |
			Soup
		>
		=>
		< 
			cnt: CNT + 1 | 
			r: 0 | 
			0 | 
			TOMnil | 
			propGen(random(CNT) , PA) :PP: PLiA |
			Soup
		>
		if propGen?(PA) == false .

The following rule terminates the initialization process and is called "randpropdone".
We can see that this rule is conditional and can only occur once

	propGen?(PLiA) == true

This can only occur if all processes in our list have the field for proposed sequence number set to 1.

	--- terminate the random generation process for proposed sequence numbers
	crl [randpropdone] :
		< 
			cnt: CNT | 
			r: 0 | 
			0 | 
			TOMnil | 
			PLiA |
			Soup
		>
		=>
		< 
			cnt: CNT | 
			r: 1 | 
			0 | 
			TOMnil | 
			PLiA |
			Soup
		>
		if propGen?(PLiA) == true .

The rule "msg" is abbreviated.
It sends a message to everyone.

	--- 1. New message placed in soup by a process for an existing account
	rl [msg] : 
		< 
			...
		> 
		=>
		< 
			...
			GMId + 1 | 
			TO :TOM: M[GMId | PidA | 0 | 0] | 
			P[PidA | AgrSeqA | PropSeqA | PropA? | DeliveredA | HoldbackA :TOM: M[GMId | PidA | 0 | 0] ] :PP: 
				PLiA |
			Soup :GM: M[GMId | PidA | 0 | 0]
		> .

* We increment global message id by one so the next message can take that number.
* The global total ordering has the new message appended to it.
* Our sender process PidA has the message added to its holdback queue
* Our message "soup" has the message added to it

Below is the reply a receiver must send back to the sender of a message.
The rule is called "repmsg".
Note that this is a conditional rule that assures that the message we wish to reply to is not one by the sender (BUG?).

	--- 2. Receiver Reply
	crl [repmsg] :
		<
			...
			P[PidA | AgrSeqA | PropSeqA | PropA? | DeliveredA | HoldbackA ] :PP:
				PLiA |
			Soup :GM: M[MId | MSrc | 0 | 0]
		>
		=>
		<
			... 
			P[PidA | AgrSeqA | PropSeqA | PropA? | DeliveredA | HoldbackA :M: M[MId | MSrc | max2(AgrSeqA, PropSeqA) + 1 | 1]] :PP:
				PLiA |
			Soup :GM: M[MId | MSrc | 0 | 0] :GM: R[MId | max2(AgrSeqA, PropSeqA) + 1 | PidA]
		> 
		if (PidA == MId) == false .

* We pull out a message from the soup to operate on.
* If the message is not sent by PidA we add the message to our holdback queue with the proposed sequence number "max2(AgrSeq, PropSeq) + 1"
* Then we push a reply back into the soup

We need to also model the crash of a process.
To do this we simple remove a process from our list of processes.

	--- Randomly crash a process
	--- 	Delete process PA from our process list
	rl [crash] : < GMId | GPid | TO | PA :PP: PLiA | Soup > => < GMId | GPid | TO | PLiA | Soup > .

## Examples of Execution

Below is an exmaple of the execution of 

	search [2] init3 =>+ < cnt: 3 | r: 1 | N:Nat | TOML:TOMsgList | PL:ProcList | GML:GMsgList > such that repIn?(GML:GMsgList) .

This command searches for two solutions from an inital of 3 processes where 

	repIn?(GML)

is true only if there is a reply in our message soup.
Therefore this is testing our system with the rules, repmsg, msg, and intiialization.

	search [2] in BANK-TRANSFERS : init3 =>+ < cnt: 3 | r: 1 | N:Nat | TOML:TOMsgList
		| PL:ProcList | GML:GMsgList > such that repIn?(GML:GMsgList) = true .

	Solution 1 (state 43)
	states: 44  rewrites: 556 in 0ms cpu (0ms real) (~ rewrites/second)
	N:Nat --> 1
	TOML:TOMsgList --> M[0 | 0 | 0 | 0]
	PL:ProcList --> P[0 | 0 | 2357136044 | 1 | TOMnil | M[0 | 0 | 0 | 0]] :PP: P[1 | 0
		| 2546248239 | 1 | TOMnil | M[0 | 0 | 2546248240 | 1]] :PP: P[2 | 0 |
		3071714933 | 1 | TOMnil | Mnil]
	GML:GMsgList --> R[0 | 2546248240 | 1] :GM: M[0 | 0 | 0 | 0]

	Solution 2 (state 44)
	states: 45  rewrites: 564 in 0ms cpu (0ms real) (~ rewrites/second)
	N:Nat --> 1
	TOML:TOMsgList --> M[0 | 0 | 0 | 0]
	PL:ProcList --> P[0 | 0 | 2357136044 | 1 | TOMnil | M[0 | 0 | 0 | 0]] :PP: P[1 | 0
		| 2546248239 | 1 | TOMnil | Mnil] :PP: P[2 | 0 | 3071714933 | 1 | TOMnil | M[0
		| 0 | 3071714934 | 1]]
	GML:GMsgList --> R[0 | 3071714934 | 2] :GM: M[0 | 0 | 0 | 0]