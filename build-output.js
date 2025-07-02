const fs = require('fs');
const path = require('path');

const outputDir = path.join('.vercel', 'output');
const staticDir = path.join(outputDir, 'static');
const functionsDir = path.join(outputDir, 'functions');
const configPath = path.join(outputDir, 'config.json');

fs.mkdirSync(staticDir, { recursive: true });
fs.mkdirSync(functionsDir, { recursive: true });

const routes = [];

// Copy static knowledge and instruction files
if (fs.existsSync('static')) {
  for (const file of fs.readdirSync('static')) {
    if (file.endsWith('.txt')) {
      fs.copyFileSync(path.join('static', file), path.join(staticDir, file));
    }
  }
}

// Create a function for each top-level Python file
for (const file of fs.readdirSync('api')) {
  if (!file.endsWith('.py')) continue;
  const name = path.basename(file, '.py');
  const funcDir = path.join(functionsDir, `api/${name}.func`);
  fs.mkdirSync(funcDir, { recursive: true });
  fs.copyFileSync(path.join('api', file), path.join(funcDir, 'index.py'));

  // copy shared requirements so the Python runtime installs dependencies
  if (fs.existsSync('requirements.txt')) {
    fs.copyFileSync('requirements.txt', path.join(funcDir, 'requirements.txt'));
  }
  const config = { runtime: 'python3.11', handler: 'index.py' };
  fs.writeFileSync(path.join(funcDir, '.vc-config.json'), JSON.stringify(config, null, 2));
  routes.push({ src: `/api/${name}`, dest: `functions/api/${name}.func` });
}

// Include maintenance task handler for /internal/(.*)
const maintSrc = path.join('api', 'maintenance', '[task].py');
if (fs.existsSync(maintSrc)) {
  const maintDir = path.join(functionsDir, 'api/maintenance/[task].func');
  fs.mkdirSync(maintDir, { recursive: true });
  fs.copyFileSync(maintSrc, path.join(maintDir, 'index.py'));
  if (fs.existsSync('requirements.txt')) {
    fs.copyFileSync('requirements.txt', path.join(maintDir, 'requirements.txt'));
  }
  const config = { runtime: 'python3.11', handler: 'index.py' };
  fs.writeFileSync(path.join(maintDir, '.vc-config.json'), JSON.stringify(config, null, 2));
  routes.push({ src: '/internal/(.*)', dest: 'functions/api/maintenance/[task].func' });
}

// Static text file route and filesystem handler
routes.push({ src: '/static/(.*)', dest: 'static/$1' });
routes.push({ handle: 'filesystem' });

fs.writeFileSync(configPath, JSON.stringify({ version: 3, routes }, null, 2));
