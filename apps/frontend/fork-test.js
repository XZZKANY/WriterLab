const { fork } = require('child_process');
const child = fork(require.resolve('./fork-child.js'), { stdio: 'inherit' });
child.on('exit', code => console.log('child-exit', code));
child.on('error', err => { console.error('child-error', err); process.exit(1); });
