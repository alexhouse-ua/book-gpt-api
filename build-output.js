const fs = require('fs');
const path = require('path');

const outputDir = path.join('.vercel', 'output');
const staticDir = path.join(outputDir, 'static');
const functionsDir = path.join(outputDir, 'functions');
const configPath = path.join(outputDir, 'config.json');

fs.mkdirSync(staticDir, { recursive: true });
fs.mkdirSync(functionsDir, { recursive: true });

// Ensure static assets are served before dynamic routes
const routes = [{ handle: 'filesystem' }];

// Copy static knowledge and instruction files
if (fs.existsSync('static')) {
  for (const file of fs.readdirSync('static')) {
    if (file.endsWith('.txt')) {
      fs.copyFileSync(path.join('static', file), path.join(staticDir, file));
    }
  }
}


// Helper to build a Python function
function buildPythonFunc(srcPath, funcRelDir, routeSrc) {
  const funcDir = path.join(functionsDir, funcRelDir);
  fs.mkdirSync(funcDir, { recursive: true });
  fs.copyFileSync(srcPath, path.join(funcDir, 'index.py'));
  if (funcRelDir.includes('maintenance/[task].func')) {
    fs.copyFileSync('maintenance_tasks.py', path.join(funcDir, 'maintenance_tasks.py'));
  }
  if (fs.existsSync('requirements.txt')) {
    fs.copyFileSync('requirements.txt', path.join(funcDir, 'requirements.txt'));
  }
  // ensure files exist before writing config
  if (!fs.existsSync(path.join(funcDir, 'index.py')) ||
      (funcRelDir.includes('maintenance/[task].func') &&
       !fs.existsSync(path.join(funcDir, 'maintenance_tasks.py')))) {
    throw new Error(`Failed to populate ${funcDir}`);
  }
  const config = { runtime: 'python3.12', handler: 'index.py' };
  fs.writeFileSync(path.join(funcDir, '.vc-config.json'), JSON.stringify(config, null, 2));
  routes.push({ src: routeSrc, dest: `functions/${funcRelDir}` });
}

// Top level api Python files
for (const file of fs.readdirSync('api')) {
  const p = path.join('api', file);
  if (fs.statSync(p).isFile() && file.endsWith('.py')) {
    const name = path.basename(file, '.py');
    buildPythonFunc(p, `api/${name}.func`, `/api/${name}`);
  }
}

// maintenance dynamic function
const maintFile = path.join('api', 'maintenance', '[task].py');
if (fs.existsSync(maintFile)) {
  buildPythonFunc(maintFile, 'api/maintenance/[task].func', '/internal/(.*)');
}

fs.writeFileSync(configPath, JSON.stringify({ version: 3, routes }, null, 2));
