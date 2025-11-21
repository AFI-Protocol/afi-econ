/**
 * Simulate Validator Rewards Command
 */

import { Command } from 'commander';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { parseEconSimConfig } from '../../configs/schema/econSimConfig.schema.js';
import { simulateValidatorRewards, type ValidatorRewardParams } from '../../models/rewards/validatorRewardModel.js';
import { createRNG } from '../../utils/rng.js';
import { logger } from '../../utils/logging.js';

export function simulateValidatorRewardsCommand(): Command {
  return new Command('simulate-validator-rewards')
    .description('Simulate validator reward distribution')
    .option('-c, --config <path>', 'Path to config file', 'src/configs/defaults/rewards.default.json')
    .action(async (options) => {
      try {
        logger.info('Loading config', { path: options.config });
        
        const configData = JSON.parse(readFileSync(options.config, 'utf-8'));
        const config = parseEconSimConfig(configData);

        const params: ValidatorRewardParams = {
          rewardPoolPerEpoch: (config.params?.rewardPoolPerEpoch as number) ?? 1000,
          validatorCount: (config.params?.validatorCount as number) ?? 10,
          performanceWeight: (config.params?.performanceWeight as number) ?? 0.6,
          stakeWeight: (config.params?.stakeWeight as number) ?? 0.4,
        };

        const rng = createRNG(config.seed);
        const results = simulateValidatorRewards(
          config.startEpoch,
          config.endEpoch,
          params,
          rng
        );

        const outputPath = join('data/out', config.output.path);
        mkdirSync(dirname(outputPath), { recursive: true });

        if (config.output.format === 'json' || config.output.format === 'both') {
          const jsonPath = outputPath.replace(/\.(csv|json)$/, '.json');
          writeFileSync(jsonPath, JSON.stringify(results, null, 2));
          logger.info('JSON output written', { path: jsonPath });
        }

        if (config.output.format === 'csv' || config.output.format === 'both') {
          const csvPath = outputPath.replace(/\.(csv|json)$/, '.csv');
          const csv = convertToCSV(results);
          writeFileSync(csvPath, csv);
          logger.info('CSV output written', { path: csvPath });
        }

        logger.info('Simulation complete');
      } catch (error) {
        logger.error('Simulation failed', error);
        process.exit(1);
      }
    });
}

function convertToCSV(data: any[]): string {
  if (data.length === 0) return '';
  const headers = Object.keys(data[0]);
  const rows = data.map(row => headers.map(h => row[h]).join(','));
  return [headers.join(','), ...rows].join('\n');
}

