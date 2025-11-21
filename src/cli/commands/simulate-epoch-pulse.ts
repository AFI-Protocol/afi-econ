/**
 * Simulate Epoch Pulse Command
 */

import { Command } from 'commander';
import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { parseEconSimConfig } from '../../configs/schema/econSimConfig.schema.js';
import { simulateEpochPulse, type EpochPulseParams } from '../../models/emissions/epochPulseModel.js';
import { createRNG } from '../../utils/rng.js';
import { logger } from '../../utils/logging.js';

export function simulateEpochPulseCommand(): Command {
  return new Command('simulate-epoch-pulse')
    .description('Simulate Epoch Pulse emissions pattern')
    .option('-c, --config <path>', 'Path to config file', 'src/configs/defaults/epochPulse.default.json')
    .action(async (options) => {
      try {
        logger.info('Loading config', { path: options.config });
        
        const configData = JSON.parse(readFileSync(options.config, 'utf-8'));
        const config = parseEconSimConfig(configData);

        logger.info('Config loaded', config);

        // Extract model-specific params
        const params: EpochPulseParams = {
          baseEmissions: (config.params?.baseEmissions as number) ?? 1000,
          pulseFrequency: (config.params?.pulseFrequency as number) ?? 10,
          pulseAmplitude: (config.params?.pulseAmplitude as number) ?? 1.5,
          decayRate: (config.params?.decayRate as number) ?? 0.01,
        };

        // Run simulation
        const rng = createRNG(config.seed);
        const results = simulateEpochPulse(
          config.startEpoch,
          config.endEpoch,
          params,
          rng
        );

        // Write output
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

