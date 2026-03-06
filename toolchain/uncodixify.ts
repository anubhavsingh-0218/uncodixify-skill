import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Represents a strict styling rule to enforce the Uncodixify aesthetic.
 */
interface DesignRule {
  readonly id: string;
  readonly pattern: RegExp;
  readonly message: string;
  readonly type: 'ban' | 'require';
}

const RULES: readonly DesignRule[] = [
  // 🚫 BANNED PATTERNS
  {
    id: 'no-large-radii',
    pattern: /\brounded-(xl|2xl|3xl|4xl|full)\b/g,
    message: 'Oversized border radii are banned. Remove them and use `rounded-sm`, `rounded-md`, or no radius.',
    type: 'ban',
  },
  {
    id: 'no-purples',
    pattern: /\b(bg|text|border|ring)-purple-\d{2,3}\b/g,
    message: 'Purples are strictly banned. Use neutral darks and approved standard accents.',
    type: 'ban',
  },
  {
    id: 'no-glassmorphism-or-gradients',
    pattern: /\b(backdrop-blur|bg-gradient-to|from-|to-|via-)\b/g,
    message: 'Gradients and glassmorphism are banned. Rely on solid dark mode surfaces.',
    type: 'ban',
  },
  {
    id: 'no-dramatic-shadows',
    pattern: /\bshadow-(lg|xl|2xl|inner)\b/g,
    message: 'Dramatic drop shadows are banned. Use subtle fine borders for depth instead.',
    type: 'ban',
  },
  {
    id: 'no-eyebrow-labels',
    pattern: /<small>/g,
    message: 'Eyebrow labels (<small>) are banned. Use standard <h1> or <h2> hierarchy.',
    type: 'ban',
  },

  // ✅ REQUIRED PATTERNS
  {
    id: 'require-fine-lines',
    pattern: /\bborder-white\/(5|10|15)\b|\bdivide-white\/(5|10|15)\b/g,
    message: 'You must use fine light white lines for structural separation (e.g., `border-white/10`).',
    type: 'require',
  },
  {
    id: 'require-dark-mode-base',
    pattern: /\b(bg-zinc-900|bg-black|bg-neutral-900|bg-zinc-950)\b/g,
    message: 'You must establish a proper dark mode base background on primary container elements.',
    type: 'require',
  },
];

/**
 * Analyzes the source code against the Uncodixify ruleset.
 * @param sourceCode The raw string content of the target file.
 * @returns An array of error strings. Returns an empty array if validation passes.
 */
function validateCode(sourceCode: string): string[] {
  const errors: string[] = [];

  for (const rule of RULES) {
    const isMatch = rule.pattern.test(sourceCode);

    if (rule.type === 'ban' && isMatch) {
      errors.push(`[VIOLATION: ${rule.id}] ${rule.message}`);
    }

    // Require rules are simplistic in regex but enforce base constraints.
    // If a file has structure but misses required utilities, flag it.
    if (rule.type === 'require' && !isMatch && sourceCode.includes('className=')) {
      errors.push(`[MISSING: ${rule.id}] ${rule.message}`);
    }
  }

  return errors;
}

/**
 * Main execution block for the CLI.
 */
function main(): void {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('Usage: npx tsx uncodixify.ts <path-to-file>');
    process.exit(1);
  }

  const targetPath = resolve(process.cwd(), args[0]);

  let sourceCode: string;
  try {
    sourceCode = readFileSync(targetPath, 'utf-8');
  } catch (err) {
    console.error(`Error reading file at ${targetPath}:`, err instanceof Error ? err.message : String(err));
    process.exit(1);
  }

  const errors = validateCode(sourceCode);

  if (errors.length > 0) {
    console.error('\n❌ Uncodixify Validation Failed\n');
    console.error('The following stylistic mistakes were detected:\n');
    for (const error of errors) {
      console.error(`  - ${error}`);
    }
    console.error('\nFix these issues and run the validator again.');
    // Exit code 1 signals to the AI agent that its task failed, prompting an automatic retry.
    process.exit(1);
  }

  console.log('✅ Uncodixify Validation Passed. Code is clean.');
  process.exit(0);
}

main();