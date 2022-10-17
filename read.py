import json
from web3 import Web3, HTTPProvider
from web3.contract import ConciseContract

myContract = json.load(open('./build/contracts/VerifyDoc.json'))
abi = myContract['abi']
bytecode = myContract['bytecode']


w3 = Web3(HTTPProvider('https://ropsten.infura.io/v3/0ba47a68dee04243bfa4b69d148ede22'))
print(w3.isConnected())
contract_address = Web3.toCheckSumAddress('')
contract = w3.eth.contract(bytecode=bytecode, abi=abi)
contract_instance = w3.eth.contract(abi=abi, address=contract_address)

print('contract value: {}'.format(contract_instance.functions.verifyDoc().call()))
