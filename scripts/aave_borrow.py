import os
from typing import Union, Tuple
from brownie import config, network
from web3 import Web3
from .eth_swap import get_weth, init_weth
from .utils import (
    approve_erc20,
    get_asset_price,
    get_permit_signature,
    FORKED_LOCAL_ENV,
    init_pool,
)


def supply_collateral(token, account, pool, amount: Union[int, float, None] = None):
    """
    To supply tokens as collateral.

    Parameters
    ----------
    token: The token collateral smart contract.
    account: The user address.
    pool: The Aave Pool contract.
    amount: `Union[int, float, None]`
        The amount of token to be supplied, without any precision.
        If None, will use the available balance instead!
    """
    # init
    if amount is None:
        supply_amount = token.balanceOf(account, {"from": account})
    else:
        supply_amount = int(amount * (10 ** token.decimals()))
    print(f"Supplying the Pool with {supply_amount} {token.symbol()} ... ")
    # approve the wrapped token transfer here
    approve_erc20(
        user=account,
        token_address=token.address,
        spender=pool.address,
        amount=supply_amount,
    )
    # supply here
    supply_tx = pool.supply(token.address, supply_amount, account, 0, {"from": account})
    supply_tx.wait(1)
    supply_event = supply_tx.events["Supply"]
    print(
        f"Successfully supplied {supply_event['amount']} {token.symbol()} on behalf "
        f"of '{supply_event['onBehalfOf']}'"
    )


def get_borrowable_data(account, pool) -> Tuple[float, float]:
    """
    Get the borrowable asset from the user account data.

    Parameters
    ----------
    account: The user address.
    pool: The Aave Pool contract.

    Returns:
    `Tuple[float, float]`: The total borrowable and debt in USD floating decimals.
    """
    (
        _total_collateral_usd,
        _total_debt_usd,
        _available_borrow_usd,
        current_liquidation_threshold,
        loan_to_value,
        health_factor,
    ) = pool.getUserAccountData(account.address)
    # convert to USD decimal
    USD_DECIMALS = 8
    total_collateral_usd = _total_collateral_usd / (10**USD_DECIMALS)
    total_debt_usd = _total_debt_usd / (10**USD_DECIMALS)
    available_borrow_usd = _available_borrow_usd / (10**USD_DECIMALS)
    print(f"User account data --- Collateral: {total_collateral_usd} USD")
    print(f"User account data --- Debt: {total_debt_usd} USD")
    print(f"User account data --- Borrowable: {available_borrow_usd} USD")
    return float(available_borrow_usd), float(total_debt_usd)


def borrow_dai(account, pool, amount_fraction):
    """
    To borrow some DAI based on a fraction of the user's borrowable fund.

    Parameters
    ----------
    account: The user address.
    pool: The Aave Pool contract.
    amount_fraction: A fraction of the borrowable fund that will be borrowed.

    Notes
    -----
    The Stable interest rate mode (1) is only available on the REAL mainnet!
    """
    network_id = network.show_active()
    borrowable_usd, _ = get_borrowable_data(account, pool)
    # get the DAI/USD conversion rate
    dai_usd_feed_address = config["networks"][network_id]["dai_usd_price_feed"]
    dai_usd_price = get_asset_price(dai_usd_feed_address)
    print(f"The DAI/USD price is at: {dai_usd_price}")
    # borrow DAI here
    borrow_usd_amount = amount_fraction * borrowable_usd  # X % of the allowed amount
    borrow_dai_amount = borrow_usd_amount / dai_usd_price
    borrow_dai_amount_precised = Web3.toWei(borrow_dai_amount, "ether")
    dai_address = config["networks"][network_id]["dai_token"]
    print(f"Borrowing {borrow_dai_amount_precised} DAI ... ")
    borrow_tx = pool.borrow(
        dai_address,
        int(borrow_dai_amount_precised),
        2,  # Interest rate mode - 1: Stable, 2: Variable
        0,  # referral code is deprecated, just use 0
        account,
        {"from": account},
    )
    borrow_tx.wait(1)
    borrow_dai_amount_event = borrow_tx.events["Borrow"]["amount"]
    _, total_debt_usd = get_borrowable_data(account, pool)
    print(
        f"Successfully borrowed {borrow_dai_amount_event} DAI! "
        f"The total debt is now at {total_debt_usd} USD"
    )
    return borrow_dai_amount_event


def repay_all(account, pool, amount, is_permit: False):
    """
    To repay the debt via EIP-2612 permit

    Parameters
    ----------
    account: The user address.
    pool: The Aave Pool contract.
    amount: The repayment amount.
    is_permit: Using the EIP-2612 permit method or not.
    """
    network_id = network.show_active()
    dai_token_address = config["networks"][network_id]["dai_token"]
    if is_permit:  # use Permit
        # get the permit signature for ERC-712 message
        sign_v, sign_r, sign_s, deadline_ts = get_permit_signature(
            token_address=dai_token_address,
            user=account,
            spender_address=pool.address,
            value=amount,
            deadline=30,  # seconds
        )
        # repay with permit here
        repay_tx = pool.repayWithPermit(
            dai_token_address,
            amount,
            2,  # interest rate mode
            account.address,
            deadline_ts,
            sign_v,
            sign_r,
            sign_s,
            {"from": account},
        )
    else:  # use the classic approval method
        # approve the DAI transfer
        approve_erc20(
            user=account,
            token_address=dai_token_address,
            spender=pool.address,
            amount=amount,
        )
        # repay here: use amount = -1 to repay all the remaining debt!
        repay_tx = pool.repay(
            dai_token_address, amount, 2, account.address, {"from": account}
        )
    repay_tx.wait(1)
    repay_amount = repay_tx.events["Repay"]["amount"]
    print(f"Successfully repaid {repay_amount} DAI!")
    # check the user account data again
    get_borrowable_data(account=account, pool=pool)


def main():
    # init basic
    use_permit = bool(int(os.getenv("USE_PERMIT", 0)))
    print(f"Permit mode: {use_permit}")
    network_id = network.show_active()
    # init contracts
    account, token = init_weth()
    pool = init_pool(account=account)
    # swap for some WETH if running on forked chain!
    if network_id in FORKED_LOCAL_ENV:
        get_weth(deposit_amount=0.1)  # in ETH
    # supply collateral
    supply_collateral(token=token, account=account, pool=pool)
    # borrow DAI here
    borrowed_amount = borrow_dai(account=account, pool=pool, amount_fraction=0.5)
    # repay all the debt here
    repay_all(account=account, pool=pool, amount=borrowed_amount, is_permit=use_permit)
    print(f"Finished!")
