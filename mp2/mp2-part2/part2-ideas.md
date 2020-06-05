# Initial Ideas
## block height
* this determines how long the chain that a miner is working on is
* this is attached to each SENDBLOCK message so that the miner knows which height it the next block should be

## SENDBLOCK
* this sends a block to other miners in the system, use the same gossip system

## REQUESTBLOCK
* if a miner detects that the height of the received block is higher than its own, it needs	to get the previous blocks to "catch up" and begin working on the new block?
* this can occur if the miner is working on block of height 2 and receives a block of height 10
* it then needs to request from whoever sent that block to get blocks 2*9 as well

## getting rid of completed transactions
* if a miner is working on block A with tx0,1,2 and it receives a block with tx0 
	it needs to stop working on the current block and create a new block with tx1,2

## confirmations
* if a transaction exists at least 6 blocks deep then we can consider it confirmed
	* https://en.bitcoin.it/wiki/Confirmation

## orderings of transactions
* it appears that the ordering of transactions do not matter and we can just
	use the order that they appeared in our queue

# Sketch of how to implement

## block
* DONE contains previous hash
* DONE block height
* DONE transactions

## storing transactions received
* whenever we receive a transaction add it to a set of transactions we need to send
* we can do this using a dictionary which preserves order
	* https://stackoverflow.com/questions/1653970/does-python-have-an-ordered-set 
	* ordered dict since we don't know what version of python the vm uses

## storing blocks
* DONE blocks are stored in a global dictionary and the key is the block height when it was generated
* DONE currently we are only using a single dictionary this appears to work in my head
* we need a list of verified blocks (or possibly a tree of blocks) that we have received
* the index represents the height of the block
* we also need a temporary list of blocks that contain unverified blocks that we have received
	* once these are verified we can add them to the verified list

## account
* DONE this needs to store the accounts and their balances
* DONE it should contain a function to update balances (or create accounts)
* DONE it should contain a function to determine if a transaction is valid
	* aka it does not result in a negative balance
	* if it does, delay it
* somewhere we need to be able to check which blocks have been confirmed and apply the transactions in the block to our accounts dictionary.  this will probably have to be another thread in network.py

## serviceThread
* this needs to now account for SOLVED receives, SOLVE sends, VERIFY sends
	* once we receive a SOLVED block, we can add it to the verified list of blocks AFTER checking if we have received other blocks that have those transactions.
		* (?? will this be handled by the rollback?) if there are new blocks received that have the transactions in the block we just verified discard it
	* once we receive a VERIFYed block, we can add it to the verified list of blocks AFTER checking if we have received other blocks that have those transactions.
		* (?? will this be handled by the rollback?) if there are new blocks received that have the transactions in the block we just verified discard it


## genBlock
* given a list of pending transactions, it needs to check that the transactions do not go negative and then generate a block and a hash.
* this hash will be sent to the service as a SOLVE request then we will wait for a SOLVED request
* this newly generated block will be added to the queue to be verified one SOLVED is returned

## gossipThreads
* this needs to now account for REQUESTBLOCK sends, RECVBLOCK, RECVOLDBLOCK recvs
	* REQUESTBLOCK: This occurs when a miner sees a higher chained block and it is not the same height they are working on.
		* These go directly into the verified queue
	* SENDBLOCK: This occurs when we wish to send a new block to our peers
	* We also need to deal with receiving a new block.  When initially received this goes into the pending block queue
		* REQUESTEDBLOCK: request block needs to edit the verified block list
			* Before deleting all of the blocks that conlfict, we need to check if there are any messages in our incorrect blocks that do not exist in the new requested blocks.  if they are there we need to readd them to our pending messages
		* SENDBLOCK: Goes into the pending block list until it is verified
			* these threads also needs to account for removing transactions that it has received from other miners from the list of transactions that it is trying to add to the blockchain
			* this can be done by editing the global dictionary storing the transactions that have yet been sent out

# Cases to think about
* receive a block with height 3 and just received a SOLVED/VERIFY of height 3
	* prioritize our own verified/solved block over the other yet to be verified one
* receive a block of height 5 and we are solving/SOLVED/VERIFY height 3
	* Request 3-4 and also re-add messages in our incorrect block 3 that do not exist in the true 3-5 yet.
	* toss away our incorrect block 3
* new node joins the network and needs to catch up to everyone