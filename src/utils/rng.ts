/**
 * Seeded Random Number Generator
 * 
 * Provides deterministic pseudo-random number generation for reproducible simulations.
 * Uses Mulberry32 algorithm for simplicity and speed.
 */

export class SeededRNG {
  private state: number;

  constructor(seed: number) {
    this.state = seed >>> 0; // Ensure unsigned 32-bit integer
  }

  /**
   * Generate next random number in range [0, 1)
   */
  next(): number {
    let t = (this.state += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /**
   * Generate random integer in range [min, max] (inclusive)
   */
  nextInt(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min;
  }

  /**
   * Generate random float in range [min, max)
   */
  nextFloat(min: number, max: number): number {
    return this.next() * (max - min) + min;
  }

  /**
   * Generate random boolean with given probability
   */
  nextBool(probability = 0.5): boolean {
    return this.next() < probability;
  }

  /**
   * Reset RNG to initial seed
   */
  reset(seed: number): void {
    this.state = seed >>> 0;
  }
}

/**
 * Create a new seeded RNG instance
 */
export function createRNG(seed: number): SeededRNG {
  return new SeededRNG(seed);
}

