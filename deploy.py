import json
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

w3 = Web3(HTTPProvider('https://ropsten.infura.io/v3/0ba47a68dee04243bfa4b69d148ede22'))
print(w3.isConnected())

key = '0x16676be3a2cf4626183ef4cf7909b26b1d2b21df50033aa8d5f6836e90fe989c'
account_address = '0x81676973515a3e1e4BE74923b1b0c001844f3aa6'


myContract = json.load(open('./build/contracts/VerifyDoc.json'))
abi = myContract['abi']
bytecode = myContract['bytecode']
contract = w3.eth.contract(bytecode=bytecode, abi=abi)

construct_txn = contract.constructor().buildTransaction({
    'from' : account_address,
    'nonce' : w3.eth.getTransactionCount(account_address), #prevent from sending transaction twice
    'gas' : 1728712,
    'gasPrice' : w3.toWei('21','gwei')})

signed = account_address.signTransaction(construct_txn)

tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
print('Transaction hash is ', tx_hash.hex())
tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
print('Contract deployed at :', tx_receipt['contractAddress'])