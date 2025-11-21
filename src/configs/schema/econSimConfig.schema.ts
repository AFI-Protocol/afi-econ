/**
 * Economic Simulation Config Schema
 * 
 * Shared Zod schema for all economic simulations.
 */

import { z } from 'zod';

/**
 * Output format options
 */
export const OutputFormatSchema = z.enum(['json', 'csv', 'both']);
export type OutputFormat = z.infer<typeof OutputFormatSchema>;

/**
 * Base configuration schema for all economic simulations
 */
export const EconSimConfigSchema = z.object({
  /** Random seed for deterministic simulation */
  seed: z.number().int().nonnegative(),

  /** Starting epoch number */
  startEpoch: z.number().int().nonnegative(),

  /** Ending epoch number */
  endEpoch: z.number().int().nonnegative(),

  /** Simulation-specific parameters (freeform) */
  params: z.record(z.unknown()).optional(),

  /** Output configuration */
  output: z.object({
    /** Output format (json, csv, or both) */
    format: OutputFormatSchema,

    /** Output file path (relative to data/out/) */
    path: z.string(),
  }),
});

export type EconSimConfig = z.infer<typeof EconSimConfigSchema>;

/**
 * Validate and parse config from unknown input
 */
export function parseEconSimConfig(input: unknown): EconSimConfig {
  return EconSimConfigSchema.parse(input);
}

