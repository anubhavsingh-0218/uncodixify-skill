import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const DARK_BASE_TOKENS = new Set(['bg-zinc-950', 'bg-zinc-900', 'bg-black', 'bg-neutral-900']);
const SEPARATOR_TOKENS = new Set([
  'border-white/5',
  'border-white/10',
  'border-white/15',
  'divide-white/5',
  'divide-white/10',
  'divide-white/15',
]);

function dedupePreserveOrder(tokens: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const token of tokens) {
    if (!token || seen.has(token)) {
      continue;
    }
    seen.add(token);
    result.push(token);
  }
  return result;
}

function normalizeToken(token: string): string[] {
  if (!token) {
    return [];
  }

  if (/^rounded-(xl|2xl|3xl|4xl|full)$/.test(token)) {
    return ['rounded-md'];
  }
  if (/^shadow-(lg|xl|2xl|inner)$/.test(token)) {
    return ['shadow-sm'];
  }
  if (/^backdrop-blur(?:-[a-z0-9-]+)?$/.test(token)) {
    return [];
  }
  if (/^bg-gradient-to-[a-z]+$/.test(token)) {
    return [];
  }
  if (/^(from|via|to)-/.test(token)) {
    return [];
  }
  if (/^(bg|text|border|ring)-purple-\d{2,3}(?:\/\d{1,3})?$/.test(token)) {
    const prefix = token.split('-')[0];
    if (prefix === 'bg') {
      return ['bg-zinc-900'];
    }
    if (prefix === 'text') {
      return ['text-zinc-200'];
    }
    return ['border-white/10'];
  }
  if (token === 'uppercase') {
    return [];
  }
  if (/^tracking-/.test(token)) {
    return [];
  }
  return [token];
}

function normalizeClassList(classes: string, options: { isRoot: boolean; preferDivide: boolean }): string {
  const rawTokens = classes.split(/\s+/).filter(Boolean);
  let tokens = dedupePreserveOrder(rawTokens.flatMap(normalizeToken));

  const hasDarkBase = tokens.some((token) => DARK_BASE_TOKENS.has(token) || /^bg-zinc-900(?:\/\d{1,3})?$/.test(token));
  const hasSeparator = tokens.some((token) => SEPARATOR_TOKENS.has(token));
  const hasBorder = tokens.includes('border') || tokens.some((token) => token.startsWith('border-'));
  const hasDivide = tokens.includes('divide-y') || tokens.some((token) => token.startsWith('divide-'));

  if (options.isRoot && !hasDarkBase) {
    tokens.unshift('bg-zinc-950');
  }

  if (!hasSeparator) {
    if (options.preferDivide || hasDivide) {
      tokens.push('divide-white/10');
    } else if (hasBorder) {
      if (!tokens.includes('border')) {
        tokens.push('border');
      }
      tokens.push('border-white/10');
    }
  }

  return dedupePreserveOrder(tokens).join(' ');
}

function normalizeClassNames(source: string): string {
  let classIndex = 0;
  return source.replace(/className="([^"]*)"/g, (fullMatch, classes: string) => {
    classIndex += 1;
    const isRoot = classIndex === 1;
    const preferDivide = /\b(grid|flex)\b/.test(classes) || /\bdivide-y\b/.test(classes);
    const normalized = normalizeClassList(classes, { isRoot, preferDivide });
    return `className="${normalized}"`;
  });
}

function replaceStructuralPatterns(source: string): string {
  let next = source;
  next = next.replace(/<small(\s|>)/g, '<p$1');
  next = next.replace(/<\/small>/g, '</p>');
  next = next.replace(/>Live pulse</g, '>Overview<');
  next = next.replace(/>Night shift</g, '>Settings<');
  next = next.replace(/>Operational clarity without the clutter\.<\/h1>/g, '>Projects</h1>');
  next = next.replace(/([ \t]+)\n/g, '\n');
  next = next.replace(/\n{3,}/g, '\n\n');
  return next;
}

function fixSource(source: string): string {
  const normalizedStructure = replaceStructuralPatterns(source);
  const normalizedClasses = normalizeClassNames(normalizedStructure);
  return normalizedClasses.trimEnd() + '\n';
}

function main(): void {
  const args = process.argv.slice(2);
  if (args.length < 1) {
    console.error('Usage: npx tsx autofix-uncodixify.ts <path-to-file>');
    process.exit(1);
  }

  const targetPath = resolve(process.cwd(), args[0]);
  const source = readFileSync(targetPath, 'utf-8');
  const fixed = fixSource(source);
  writeFileSync(targetPath, fixed, 'utf-8');
}

main();
