from typing import Optional
from datetime import datetime as dt, timedelta as td
from brownie import accounts, chain, config, network, interface, Contract
from eth_account import Account
from web3 import Web3


# chain required for Mocking
LOCAL_BLOCKCHAIN_ENV = [
    "development",  # run using ganache-cli
    "ganache-local",  # ganache UI for mock contract deployment!
]
# chain required for Forking
FORKED_LOCAL_ENV = [
    "mainnet-fork",  # Ganache CLI, ethereum mainnet forked
]
BURN_ADDRESS = "0x0000000000000000000000000000000000000000"


def approve_erc20(user, token_address, spender, amount):
    """
    To approve ERC20 token transaction.

    Parameters
    ----------
    user: The account that own the fund.
    token_address: `str`
        The token's deployed smart contract address.
    spender: `str`
        The address of the contract that would perform transfer on behalf of the user.
    amount: `int`
        The token amount that will be approved.
    """
    token = interface.IERC20(token_address)
    print(f"Approving {amount} {token.symbol()} for contract: '{spender}' ... ")
    approve_tx = token.approve(spender, amount, {"from": user})
    approve_tx.wait(1)
    return approve_tx


def get_account(index=None, id=None, use_local=False):
    if index is not None:
        # automatically use stored account via indexing
        return accounts[index]
    if id is not None:
        # get from the stored account in brownie
        return accounts.load(id)

    if (
        network.show_active() in LOCAL_BLOCKCHAIN_ENV
        or network.show_active() in FORKED_LOCAL_ENV
    ):
        if use_local:  # use brownie LocalAccount!
            local = accounts.add(config["wallets"]["key_playground"])
            if local.balance() == 0:  # fund account if empty
                accounts[0].transfer(local, "10 ether")
            print(
                f"Using permit method - Local balance: "
                f"{Web3.fromWei(local.balance(), 'ether')} ETH"
            )
            return local
        else:
            return accounts[0]
    return accounts.add(config["wallets"]["key_playground"])


def get_asset_price(data_feed_address):
    """
    To get the price data for specific pairs.

    Parameters
    ----------
    data_feed_address: `str`
        The Chainlink data feed address for specific pairs.
    """
    data_feed = interface.AggregatorV3Interface(data_feed_address)
    _, latest_price, _, _, _ = data_feed.latestRoundData()
    return float(latest_price / (10 ** data_feed.decimals()))


def build_permit_erc712(token, user, spender_address, value, deadline_ts):
    """
    To build the ERC-712 message for the ERC-20 permit.
    """
    # TODO: build using the eip712 module by Apeworx
    nonce = chain[-1] + 1
    return None


def get_permit_signature(
    token_address, user, spender_address, value, deadline: Optional[int] = None
):
    # init
    token = interface.IERC20(token_address)
    deadline = 10 if deadline is None else deadline  # in seconds
    deadline_ts = int((dt.now() + td(seconds=deadline)).timestamp())

    # Generate the permit data hash
    permit_erc712_message = build_permit_erc712(
        token=token,
        user=user,
        spender_address=spender_address,
        value=value,
        deadline_ts=deadline_ts,
    )
    # Sign the permit data
    signed_message = user.sign_message(permit_erc712_message)
    # Extract the v, r, and s values from the signature
    v = signed_message.v
    r = Web3.toHex(signed_message.r)
    s = Web3.toHex(signed_message.s)
    return v, r, s, deadline_ts


def init_pool(account):
    """
    Initialize the pool contract
    """
    pool_proxy_address = config["networks"][network.show_active()]["pool_proxy"]
    pool = interface.IPool(pool_proxy_address)
    user_data = pool.getUserAccountData(account, {"from": account})
    print(f"The user's Pool (interface) data: {user_data}")
    return pool


def init_pool_from_explorer(account):
    """
    Initialize the pool contract
    """
    pool_proxy_address = config["networks"][network.show_active()]["pool_proxy"]
    pool = Contract.from_explorer(pool_proxy_address)
    user_data = pool.getUserAccountData(account, {"from": account})
    print(f"The user's Pool (explorer) data: {user_data}")
    return pool


def main():
    print("Finished!")
