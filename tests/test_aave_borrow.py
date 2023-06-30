from scripts.utils import (
    approve_erc20,
    get_account,
    get_asset_price,
    init_pool,
)
from brownie import config, network
from web3 import Web3


def test_get_asset_price():
    # Arrange / Act
    dai_usd_address = config["networks"][network.show_active()]["dai_usd_price_feed"]
    asset_price = get_asset_price(dai_usd_address)
    # Assert
    assert asset_price != 0


def test_get_pool():
    # Arrange / Act
    pool = init_pool(account=get_account())
    # Assert
    assert pool is not None


def test_approve_erc20():
    # Arrange
    account = get_account()
    pool = init_pool(account=account)
    amount = Web3.toWei(1, "ether")
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    # Act
    approve_tx = approve_erc20(account, erc20_address, pool.address, amount)
    approve_tx_event = approve_tx.events["Approval"]
    # Assert
    assert approve_tx_event is not None
