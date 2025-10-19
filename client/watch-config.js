#!/usr/bin/env node
/**
 * Watch staticwebapp.config.local.json and copy to staticwebapp.config.json on change
 */
import { watch } from 'fs';
import { copyFileSync } from 'fs';
import { resolve } from 'path';

const source = resolve('staticwebapp.config.local.json');
const dest = resolve('staticwebapp.config.json');

// Initial copy
copyFileSync(source, dest);
console.log('✓ Copied staticwebapp.config.local.json → staticwebapp.config.json');

// Watch for changes
watch(source, (eventType) => {
  if (eventType === 'change') {
    copyFileSync(source, dest);
    console.log('✓ Config updated: staticwebapp.config.local.json → staticwebapp.config.json');
  }
});

console.log('👀 Watching staticwebapp.config.local.json for changes...');
