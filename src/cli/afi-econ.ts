#!/usr/bin/env node

/**
 * afi-econ CLI
 * 
 * Command-line interface for running economic simulations.
 */

import { Command } from 'commander';
import { simulateEpochPulseCommand } from './commands/simulate-epoch-pulse.js';
import { simulateMintingCommand } from './commands/simulate-minting.js';
import { simulateValidatorRewardsCommand } from './commands/simulate-validator-rewards.js';
import { simulateSignalEconomyCommand } from './commands/simulate-signal-economy.js';

const program = new Command();

program
  .name('afi-econ')
  .description('AFI Protocol Economic Simulation Toolkit')
  .version('0.1.0');

// Register commands
program.addCommand(simulateEpochPulseCommand());
program.addCommand(simulateMintingCommand());
program.addCommand(simulateValidatorRewardsCommand());
program.addCommand(simulateSignalEconomyCommand());

program.parse();

