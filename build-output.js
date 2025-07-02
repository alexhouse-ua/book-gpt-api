const fs = require('fs');
const path = require('path');

const outputDir = path.join('.vercel', 'output');
const staticDir = path.join(outputDir, 'static');
const functionsDir = path.join(outputDir, 'functions');
const configPath = path.join(outputDir, 'config.json');

fs.mkdirSync(staticDir, { recursive: true });
fs.mkdirSync(functionsDir, { recursive: true });

const routes = [];

// Copy any .txt files from api to static (as previous script did)
for (const file of fs.readdirSync('api')) {
  if (file.endsWith('.txt')) {
    fs.copyFileSync(path.join('api', file), path.join(staticDir, file));
  }
}

// Create a function for each Python file
for (const file of fs.readdirSync('api')) {
  if (!file.endsWith('.py')) continue;
  const name = path.basename(file, '.py');
  const funcDir = path.join(functionsDir, `api/${name}.func`);
  fs.mkdirSync(funcDir, { recursive: true });
  fs.copyFileSync(path.join('api', file), path.join(funcDir, 'index.py'));
  const config = { runtime: 'python3.11', handler: 'index.py' };
  fs.writeFileSync(path.join(funcDir, '.vc-config.json'), JSON.stringify(config, null, 2));
  routes.push({ src: `/api/${name}`, dest: `functions/api/${name}.func` });
}

fs.writeFileSync(configPath, JSON.stringify({ version: 3, routes }, null, 2));
