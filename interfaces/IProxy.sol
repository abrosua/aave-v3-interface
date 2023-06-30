// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IProxy {
    event Upgraded(address indexed implementation);

    function admin() external returns (address);

    function implementation() external returns (address);

    function initialize(address _logic, bytes memory _data) external payable;

    function upgradeTo(address newImplementation) external;

    function upgradeToAndCall(
        address newImplementation,
        bytes memory data
    ) external payable;
}
