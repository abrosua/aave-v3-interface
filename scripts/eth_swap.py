import os
from .utils import get_account
from brownie import interface, config, network
from web3 import Web3


def init_weth():
    """
    To initialize the WETH interface and account to use.
    """
    use_permit = bool(int(os.getenv("USE_PERMIT", 0)))
    account = get_account(use_local=use_permit)
    weth = interface.IWETH(config["networks"][network.show_active()]["weth_token"])
    return account, weth


def get_weth(deposit_amount):
    """
    Depositing ETH to the WETH contract will mint same amount WETH as the result.
    """
    account, weth = init_weth()
    # mint WETH by depositing ETH to the WETH contract
    mint_tx = weth.deposit(
        {"from": account, "value": Web3.toWei(deposit_amount, "ether")}
    )
    mint_tx.wait(1)
    print(f"Received {deposit_amount} ETH!")
    return mint_tx


def withdraw_eth(wd_amount):
    """
    Withdrawing ETH from the WETH contract will burn the same amount of WETH.
    """
    account, weth = init_weth()
    # burn the WETH by withdrawing ETH from the WETH contract
    burn_tx = weth.withdraw(Web3.toWei(wd_amount, "ether"), {"from": account})
    burn_tx.wait(1)
    print(f"Withdrew {burn_tx.events['Withdrawal']['wad']}")
    return burn_tx


def main():
    # get_weth(deposit_amount=0.17)  # in ETH
    withdraw_eth(wd_amount=0.07)  # in ETH
