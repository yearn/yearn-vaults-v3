# @version 0.3.4

event AddedToWhitelist:
    account: address 
event RemovedFromWhitelist:
    account: address 

whitelist: HashMap[address,bool]
owner: public(address)

@external
def __init__():
    self.owner = msg.sender

@external
def add_to_whitelist(_address: address):
    assert msg.sender == self.owner, "not owner"
    self.whitelist[_address] = True
    log AddedToWhitelist(_address)

@external
def remove_from_whitelist(_address: address):
    assert msg.sender == self.owner, "not owner"
    self.whitelist[_address] = False
    log RemovedFromWhitelist(_address)

@view
@external
def is_whitelisted(_address: address) -> bool:
    return self.whitelist[_address]
